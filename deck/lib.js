// Shared helpers for the JWT custom-claim design guide
const pptxgen = require('pptxgenjs');
const React = require('react');
const ReactDOMServer = require('react-dom/server');
const sharp = require('sharp');
const md = require('react-icons/md');

const THEME = {
  name: 'Claims Slate',
  headFontFace: 'BIZ UDPGothic',
  bodyFontFace: 'BIZ UDPGothic',
  colors: {
    dk1: '17202B', lt1: 'FFFFFF', dk2: '13324A', lt2: 'EDF2F4',
    accent1: '0B6E78', accent2: 'D18A0B', accent3: 'C2413B', accent4: '3B8458',
    accent5: '4E6A86', accent6: '7A5BA8', hlink: '0B6E78', folHlink: '4E6A86',
  },
};
const HEX = THEME.colors;
const MUTED = '6B7883';
const BORDER = 'D3DCDF';
const MONO = 'BIZ UDGothic';

const ICONS = {};
async function prepIcons(names) {
  for (const n of names) {
    const Comp = md[n];
    if (!Comp) throw new Error('Unknown icon ' + n);
    for (const col of ['FFFFFF', HEX.dk2]) {
      const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Comp, { size: 256, color: '#' + col }));
      const buf = await sharp(Buffer.from(svg)).resize(256, 256).png().toBuffer();
      ICONS[n + ':' + col] = 'image/png;base64,' + buf.toString('base64');
    }
  }
}

function makeLib() {
  const pres = new pptxgen();
  pres.layout = 'LAYOUT_WIDE'; // 13.333 x 7.5
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  pres.title = 'JWT クレーム設計ガイド：組織で共用する独自クレーム';
  pres.subject = '新任テックリーダー向け：独自クレームの設計・伝搬・検証・ガバナンス';
  pres.author = 'Takenori Kusaka';
  const C = pres.SchemeColor;
  const SH = pres.shapes;

  pres.defineSlideMaster({ title: 'TITLE', background: { color: C.text2 }, objects: [] });
  pres.defineSlideMaster({
    title: 'SECTION', background: { color: C.text2 },
    objects: [{ placeholder: { options: { name: 'title', type: 'title', x: 0.8, y: 2.55, w: 6.0, h: 1.9, fontSize: 36, bold: true, color: C.background1, valign: 'top', align: 'left', margin: 0 }, text: '' } }],
    slideNumber: { x: 12.2, y: 7.0, w: 0.5, h: 0.3, fontSize: 10, color: 'A9BCC2', align: 'right' },
  });
  pres.defineSlideMaster({
    title: 'CONTENT', background: { color: C.background1 },
    objects: [
      { placeholder: { options: { name: 'title', type: 'title', x: 0.6, y: 0.58, w: 12.1, h: 0.68, fontSize: 28, bold: true, color: C.text2, valign: 'middle', margin: 0 }, text: '' } },
      { text: { text: 'JWT クレーム設計ガイド｜組織で共用する独自クレーム', options: { x: 0.6, y: 7.05, w: 6, h: 0.3, fontSize: 10, color: MUTED, margin: 0 } } },
    ],
    slideNumber: { x: 12.2, y: 7.05, w: 0.5, h: 0.3, fontSize: 10, color: MUTED, align: 'right' },
  });

  let curSection = null;
  const L = { pres, C, SH, MUTED, BORDER, HEX, MONO };

  // Stable slide IDs (issue #15). Every slide is declared with an explicit `id` ("pNN-kebab-slug"),
  // independent of its position, so references survive slide insertion. The IDs are collected
  // here in slide order and written by build.js to deck/slide_ids.json; nothing is rendered.
  L.part = null; // set by build.js to the part being loaded ("p04")
  L.slideIds = [];
  const ID_RE = /^p\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*$/;
  const track = (id, title) => {
    if (!id) throw new Error('slide without id: ' + title);
    if (!ID_RE.test(id)) throw new Error('bad slide id (want pNN-kebab-slug): ' + id);
    if (L.part && !id.startsWith(L.part + '-')) throw new Error('slide id ' + id + ' is declared in ' + L.part + '.js');
    if (L.slideIds.some((x) => x.id === id)) throw new Error('duplicate slide id: ' + id);
    L.slideIds.push({ n: L.slideIds.length + 1, id, part: L.part, title: String(title).replace(/\s+/g, ' ').trim() });
  };

  // raw slide (e.g. the title slide): pres.addSlide options plus { id, title }
  L.slide = (o) => {
    const { id, title, ...opt } = o;
    track(id, title || '');
    return pres.addSlide(opt);
  };

  L.section = (title) => { pres.addSection({ title }); curSection = title; };

  // evidence line: three kinds of basis, shown on the slide foot (spec / institution / Japanese book)
  L.refs = (s, r) => {
    const K = [['spec', '仕様', C.accent1], ['inst', '指針', C.accent4], ['book', '書籍', C.accent2]].filter(([k]) => r[k]);
    let x = 0.6;
    const w = (12.1 - (K.length - 1) * 0.12) / Math.max(1, K.length);
    K.forEach(([k, lab, col]) => {
      s.addText([{ text: lab + '  ', options: { bold: true, color: col } }, { text: r[k], options: { color: MUTED } }],
        { isTextBox: true, x, y: 6.62, w, h: 0.38, fontSize: 9.5, margin: 0, valign: 'middle', fit: 'shrink' });
      x += w + 0.12;
    });
  };

  L.T = (s, text, o = {}) => {
    s.addText(text, Object.assign({ isTextBox: true, fontSize: 14, color: C.text1, margin: 0.04, valign: 'top' }, o));
  };

  // items: string | [boldPrefix, rest]; returns text runs
  L.runs = (items, o = {}) => {
    const out = [];
    const bullet = o.bullet === undefined ? true : o.bullet;
    items.forEach((it, i) => {
      const last = i === items.length - 1;
      const pOpt = { bullet: bullet ? { indent: 14 } : false, paraSpaceAfter: o.space === undefined ? 6 : o.space };
      if (o.color) pOpt.color = o.color;
      if (Array.isArray(it)) {
        out.push({ text: it[0], options: Object.assign({}, pOpt, { bold: true, color: o.boldColor || o.color || C.text1 }) });
        out.push({ text: it[1], options: { breakLine: !last, color: o.color || C.text1 } });
      } else {
        out.push({ text: it, options: Object.assign({}, pOpt, { breakLine: !last }) });
      }
    });
    return out;
  };

  L.bullets = (s, items, o) => {
    L.T(s, L.runs(items, o), Object.assign({ fontSize: 14 }, o, { bullet: undefined, space: undefined, boldColor: undefined }));
  };

  L.icon = (s, name, x, y, d, color, dark) => {
    s.addShape(SH.OVAL, { x, y, w: d, h: d, fill: { color: color || C.accent1 }, line: { color: color || C.accent1 }, objectName: 'icon-bg-' + name });
    const p = d * 0.22;
    s.addImage({ data: ICONS[name + ':' + (dark ? HEX.dk2 : 'FFFFFF')], x: x + p, y: y + p, w: d - 2 * p, h: d - 2 * p, altText: name.replace(/^Md/, '') + ' icon' });
  };

  L.crumb = (s, act) => {
    if (!act) return;
    const STAGES = ['定義', '発行', '伝搬', '検証', '認可', '運用'];
    STAGES.forEach((t, i) => {
      const on = act.includes(i);
      s.addText(t, { shape: SH.ROUNDED_RECTANGLE, rectRadius: 0.14, x: 6.5 + i * 1.04, y: 0.18, w: 0.98, h: 0.28, fill: { color: on ? C.accent1 : C.background2 }, line: { color: on ? C.accent1 : C.background2 }, fontSize: 10, bold: on, color: on ? C.background1 : MUTED, align: 'center', valign: 'middle', margin: 0, objectName: 'stage-' + i });
    });
  };

  L.content = (title, o = {}) => {
    track(o.id, title);
    const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: curSection });
    s.addText(title, { placeholder: 'title' });
    L.crumb(s, o.stages);
    if (o.tag) {
      s.addText(o.tag, { shape: SH.ROUNDED_RECTANGLE, rectRadius: 0.14, x: 0.6, y: 0.18, w: 1.5, h: 0.28, fill: { color: C.accent5, transparency: 85 }, line: { color: C.accent5 }, fontSize: 10, color: C.accent5, bold: true, align: 'center', valign: 'middle', margin: 0 });
    }
    if (o.lead) L.T(s, o.lead, { x: 0.6, y: 1.3, w: 12.1, h: 0.5, fontSize: 17, color: C.accent1, bold: true, valign: 'middle', margin: 0 });
    if (o.refs) L.refs(s, o.refs);
    if (o.src) L.T(s, '出典: ' + o.src, { x: 0.6, y: 6.68, w: 11.4, h: 0.32, fontSize: 10, color: MUTED, valign: 'middle', margin: 0 });
    if (o.notes) s.addNotes(o.notes);
    return s;
  };

  L.divider = (no, title, sub, qs, notes, o = {}) => {
    track(o.id, title);
    const s = pres.addSlide({ masterName: 'SECTION', sectionTitle: curSection });
    L.T(s, no, { x: 0.8, y: 1.85, w: 4, h: 0.55, fontSize: 20, bold: true, color: C.accent2, margin: 0, charSpacing: 4 });
    s.addText(title, { placeholder: 'title' });
    L.T(s, sub, { x: 0.8, y: 4.55, w: 5.9, h: 1.2, fontSize: 16, color: C.background2, margin: 0 });
    s.addShape(SH.ROUNDED_RECTANGLE, { x: 7.3, y: 1.6, w: 5.4, h: 4.4, rectRadius: 0.1, fill: { color: C.background1, transparency: 90 }, line: { color: 'A9BCC2', width: 0.75 } });
    L.T(s, 'このPartで答えられるようになる問い', { x: 7.6, y: 1.85, w: 4.9, h: 0.45, fontSize: 15, bold: true, color: C.accent2, margin: 0 });
    L.T(s, L.runs(qs, { color: C.background1, space: 10 }), { x: 7.6, y: 2.45, w: 4.9, h: 3.4, fontSize: 15, color: C.background1, margin: 0 });
    if (notes) s.addNotes(notes);
    return s;
  };

  L.card = (s, o) => {
    const { x, y, w, h } = o;
    const fill = o.fill || C.background2;
    s.addShape(SH.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: fill }, line: { color: o.line || fill, width: 0.75 }, objectName: 'card' });
    let tx = x + 0.2;
    const top = y + (o.pad || 0.18);
    if (o.icon) { L.icon(s, o.icon, x + 0.2, top, 0.52, o.color); tx = x + 0.88; }
    const th = o.titleH || 0.52;
    L.T(s, o.title, { x: tx, y: top, w: x + w - tx - 0.12, h: th, fontSize: o.titleSize || 16, bold: true, color: o.titleColor || C.text1, valign: 'middle', margin: 0 });
    if (o.body) {
      const by = top + th + 0.14;
      const isRuns = Array.isArray(o.body) && o.body[0] && typeof o.body[0] === 'object' && !Array.isArray(o.body[0]);
      const body = Array.isArray(o.body) && !isRuns ? L.runs(o.body, { space: 4 }) : o.body;
      L.T(s, body, { x: x + 0.2, y: by, w: w - 0.4, h: y + h - by - 0.12, fontSize: o.bodySize || 14, margin: 0, color: o.bodyColor || C.text1 });
    }
  };

  L.note = (s, kind, text, o) => {
    const K = {
      leader: { icon: 'MdFlag', color: C.accent2, label: 'リーダーの視点' },
      warn: { icon: 'MdWarning', color: C.accent3, label: '注意' },
      tip: { icon: 'MdLightbulb', color: C.accent1, label: 'ポイント' },
      add: { icon: 'MdLibraryAdd', color: C.accent5, label: '補足（元レポート外の一般知識）' },
      decide: { icon: 'MdGavel', color: C.accent4, label: '採用判断' },
    }[kind];
    const { x, y, w, h } = o;
    s.addShape(SH.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: K.color, transparency: 88 }, line: { color: K.color, width: 1 }, objectName: 'note-' + kind });
    const d = Math.min(0.46, h - 0.2);
    L.icon(s, K.icon, x + 0.16, h < 0.8 ? y + (h - d) / 2 : y + 0.16, d, K.color);
    const label = o.label !== undefined ? o.label : K.label;
    const body = Array.isArray(text) ? text : [{ text, options: {} }];
    L.T(s, (label ? [{ text: label, options: { bold: true, fontSize: 12, color: C.text1, breakLine: true } }] : []).concat(body), { x: x + 0.78, y: y + 0.12, w: w - 0.95, h: h - 0.2, fontSize: o.size || 14, margin: 0, valign: o.valign || 'top', paraSpaceAfter: 2 });
  };

  // rows[0] = header
  L.table = (s, rows, o) => {
    const fs = o.fontSize || 12;
    const data = rows.map((r, ri) => r.map((c, ci) => {
      const opt = { fontSize: fs, valign: 'middle', margin: [0.04, 0.08, 0.04, 0.08], border: { type: 'solid', pt: 0.5, color: BORDER } };
      if (ri === 0) Object.assign(opt, { bold: true, color: C.background1, fill: { color: o.headFill || C.text2 }, fontSize: fs });
      else {
        Object.assign(opt, { color: C.text1, fill: { color: ri % 2 === 0 ? C.background2 : C.background1 } });
        if (ci === 0 && o.firstBold !== false) opt.bold = true;
        if (o.colColor && o.colColor[ci]) opt.color = o.colColor[ci];
      }
      if (c && typeof c === 'object' && !Array.isArray(c)) return { text: c.text, options: Object.assign(opt, c.options || {}) };
      return { text: c, options: opt };
    }));
    const t = { x: o.x, y: o.y, w: o.w, colW: o.colW, autoPage: false };
    if (o.rowH) t.rowH = o.rowH;
    s.addTable(data, t);
  };

  L.box = (s, text, o) => {
    s.addText(text, Object.assign({ shape: SH.ROUNDED_RECTANGLE, rectRadius: 0.08, fill: { color: o.fill || C.accent1 }, line: { color: o.lineColor || o.fill || C.accent1, width: 1 }, color: o.color || C.background1, fontSize: o.fontSize || 14, bold: o.bold === undefined ? true : o.bold, align: o.align || 'center', valign: 'middle', margin: 0.06 }, o, { fill: { color: o.fill || C.accent1, transparency: o.transparency || 0 } }));
  };

  // straight arrows; dir: r,l,d,u
  L.arrow = (s, x, y, len, dir, color, w) => {
    const line = { color: color || MUTED, width: w || 1.75, endArrowType: 'triangle' };
    if (dir === 'r') s.addShape(SH.LINE, { x, y, w: len, h: 0, line });
    if (dir === 'l') s.addShape(SH.LINE, { x: x - len, y, w: len, h: 0, line, flipH: true });
    if (dir === 'd') s.addShape(SH.LINE, { x, y, w: 0, h: len, line });
    if (dir === 'u') s.addShape(SH.LINE, { x, y: y - len, w: 0, h: len, line, flipV: true });
  };

  // horizontal process: steps [{t,d,fill}]
  L.flow = (s, steps, o) => {
    const n = steps.length, gap = o.gap || 0.38;
    const bw = (o.w - gap * (n - 1)) / n;
    steps.forEach((st, i) => {
      const x = o.x + i * (bw + gap);
      const fill = st.fill || o.fill || C.accent1;
      s.addShape(SH.ROUNDED_RECTANGLE, { x, y: o.y, w: bw, h: o.h, rectRadius: 0.08, fill: { color: fill, transparency: st.tr || 0 }, line: { color: fill }, objectName: 'flow-step' });
      const tc = st.tc || C.background1;
      const tr = [{ text: st.t, options: { bold: true, fontSize: o.tSize || 15, color: tc, breakLine: !!st.d } }];
      if (st.d) tr.push({ text: st.d, options: { fontSize: o.dSize || 12, color: tc } });
      L.T(s, tr, { x: x + 0.08, y: o.y + 0.08, w: bw - 0.16, h: o.h - 0.16, align: o.align || 'center', valign: o.valign || 'middle', margin: 0, paraSpaceAfter: 4 });
      if (i < n - 1) L.arrow(s, x + bw + 0.05, o.y + o.h / 2, gap - 0.1, 'r', o.arrowColor);
    });
  };

  L.stat = (s, o) => {
    L.T(s, o.value, { x: o.x, y: o.y, w: o.w, h: o.vh || 0.95, fontSize: o.size || 44, bold: true, color: o.color || C.accent1, margin: 0, valign: 'bottom', align: o.align || 'left' });
    L.T(s, o.label, { x: o.x, y: o.y + (o.vh || 0.95) + 0.05, w: o.w, h: o.lh || 0.7, fontSize: o.lsize || 13, color: C.text1, margin: 0, align: o.align || 'left' });
  };

  L.bar = (s, o) => {
    const opts = {
      x: o.x, y: o.y, w: o.w, h: o.h, barDir: o.dir || 'col', chartColors: o.colors || [HEX.accent1],
      showValue: true, dataLabelPosition: 'outEnd', dataLabelFontSize: 12, dataLabelFontFace: '+mn-lt', dataLabelColor: HEX.dk1,
      catAxisLabelFontFace: '+mn-lt', catAxisLabelFontSize: 12, catAxisLabelColor: HEX.dk1,
      valAxisLabelFontFace: '+mn-lt', valAxisLabelFontSize: 10, valAxisLabelColor: MUTED,
      valGridLine: { color: 'E3E8EA', size: 0.5 }, catGridLine: { style: 'none' },
      showLegend: !!o.legend, legendPos: 'b', legendFontFace: '+mn-lt', legendFontSize: 11, legendColor: HEX.dk1,
      showTitle: !!o.title, title: o.title, titleFontFace: '+mn-lt', titleFontSize: 13, titleColor: HEX.dk1,
      barGapWidthPct: 60,
    };
    if (o.max !== undefined) opts.valAxisMaxVal = o.max;
    if (o.min !== undefined) opts.valAxisMinVal = o.min;
    if (o.fmt) opts.dataLabelFormatCode = o.fmt;
    const series = o.series || [{ name: o.name || 'value', labels: o.labels, values: o.values }];
    s.addChart(pres.charts.BAR, series, opts);
  };

  // line chart: series [{name, labels, values}]
  L.line = (s, o) => {
    s.addChart(pres.charts.LINE, o.series, {
      x: o.x, y: o.y, w: o.w, h: o.h, chartColors: o.colors || [HEX.accent1, HEX.accent3, HEX.accent2],
      lineSize: 2, lineDataSymbol: 'circle', lineDataSymbolSize: 7, showValue: !!o.showValue, dataLabelFormatCode: o.fmt || '0%', dataLabelPosition: 't',
      dataLabelFontFace: '+mn-lt', dataLabelFontSize: 11, dataLabelColor: HEX.dk1,
      catAxisLabelFontFace: '+mn-lt', catAxisLabelFontSize: 12, catAxisLabelColor: HEX.dk1, catAxisTitle: o.catTitle, showCatAxisTitle: !!o.catTitle,
      catAxisTitleFontFace: '+mn-lt', catAxisTitleFontSize: 11, catAxisTitleColor: MUTED,
      valAxisLabelFontFace: '+mn-lt', valAxisLabelFontSize: 10, valAxisLabelColor: MUTED, valAxisMinVal: o.min === undefined ? 0 : o.min, valAxisMaxVal: o.max === undefined ? 1 : o.max,
      valAxisLabelFormatCode: o.fmt || '0%', valGridLine: { color: 'E3E8EA', size: 0.5 }, catGridLine: { style: 'none' },
      showLegend: true, legendPos: 'b', legendFontFace: '+mn-lt', legendFontSize: 11, legendColor: HEX.dk1,
      showTitle: !!o.title, title: o.title, titleFontFace: '+mn-lt', titleFontSize: 13, titleColor: HEX.dk1,
    });
  };

  L.code = (s, code, o) => {
    s.addShape(SH.ROUNDED_RECTANGLE, { x: o.x, y: o.y, w: o.w, h: o.h, rectRadius: 0.06, fill: { color: C.text1 }, line: { color: C.text1 } });
    L.T(s, code, { x: o.x + 0.15, y: o.y + 0.1, w: o.w - 0.3, h: o.h - 0.2, fontFace: MONO, fontSize: o.fontSize || 11, color: 'E6EDF0', margin: 0 });
  };

  return L;
}

module.exports = { makeLib, prepIcons, THEME };
