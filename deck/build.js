const fs = require('fs');
const path = require('path');
const { makeLib, prepIcons, THEME } = require('./lib');
const { applyTheme } = require('./theme');
const PARTS = ['p00', 'p01', 'p02', 'p03', 'p04', 'p05', 'p06', 'p07', 'p08', 'p09', 'p10', 'p11', 'p12'].filter((p) => fs.existsSync(path.join(__dirname, p + '.js')));
// usage: node build.js [out.pptx] [--ids-only] [--register] [--ids-out <file>]
//   --ids-only  collect the slide IDs and write the ID file, without writing the PPTX
//   --register  append IDs that are not in slide_ids_registry.json yet (issuing them today)
//   --ids-out   where to write the ID file (default: slide_ids.json next to this script)
// Slide IDs (issue #15): slide_ids.json lists the IDs in slide order; slide_ids_registry.json is the
// append-only record of every ID ever issued (first title, issue date, retitled / retired entries).
const args = process.argv.slice(2);
const flag = (k) => { const i = args.indexOf(k); if (i < 0) return false; args.splice(i, 1); return true; };
const opt = (k) => { const i = args.indexOf(k); if (i < 0) return null; const v = args[i + 1]; args.splice(i, 2); return v; };
const idsOnly = flag('--ids-only');
const register = flag('--register');
const idsOut = opt('--ids-out') || path.join(__dirname, 'slide_ids.json');
const REGISTRY = path.join(__dirname, 'slide_ids_registry.json');

function today() {
  if (process.env.SLIDE_ID_DATE) return process.env.SLIDE_ID_DATE;
  const d = new Date();
  return [d.getFullYear(), String(d.getMonth() + 1).padStart(2, '0'), String(d.getDate()).padStart(2, '0')].join('-');
}

// Structural registry rules. Title drift is checked by tools/check_slide_refs.py.
function checkRegistry(ids, reg) {
  const errors = [];
  const seen = new Set(ids.map((x) => x.id));
  const fresh = ids.filter((x) => !Object.prototype.hasOwnProperty.call(reg, x.id));
  if (fresh.length && !register) {
    fresh.forEach((x) => errors.push('slide ' + x.n + ': id ' + x.id + ' is not in slide_ids_registry.json (new slide? run: node build.js --ids-only --register)'));
  }
  if (register) fresh.forEach((x) => { reg[x.id] = { issued: today(), title: x.title }; console.log('registered', x.id); });
  Object.entries(reg).forEach(([id, e]) => {
    if (!e.retired && !seen.has(id)) errors.push('id ' + id + ' (' + e.title + ') is in the registry but no slide has it: restore it, or mark it "retired" in slide_ids_registry.json');
  });
  return errors;
}

(async () => {
  const src = ['lib.js', ...PARTS.map((p) => p + '.js')].map((f) => fs.readFileSync(path.join(__dirname, f), 'utf8')).join('\n');
  const names = [...new Set(src.match(/'Md[A-Za-z]+'/g).map((s) => s.slice(1, -1)))];
  await prepIcons(names);
  const L = makeLib();
  const reg = fs.existsSync(REGISTRY) ? JSON.parse(fs.readFileSync(REGISTRY, 'utf8')) : {};
  L.registry = reg;
  PARTS.forEach((p) => { L.part = p; require('./' + p)(L); });
  const errors = checkRegistry(L.slideIds, reg);
  if (errors.length) { errors.forEach((e) => console.error('ERROR', e)); process.exit(1); }
  if (register) fs.writeFileSync(REGISTRY, JSON.stringify(reg, null, 1) + '\n', 'utf8');
  fs.writeFileSync(idsOut, JSON.stringify(L.slideIds, null, 1) + '\n', 'utf8');
  console.log('slide ids', L.slideIds.length, '->', idsOut);
  if (idsOnly) return;
  const out = args[0] || 'JWT_クレーム設計ガイド.pptx';
  await L.pres.writeFile({ fileName: out });
  await applyTheme(out, THEME);
  console.log('wrote', out);
})().catch((e) => { console.error(e); process.exit(1); });
