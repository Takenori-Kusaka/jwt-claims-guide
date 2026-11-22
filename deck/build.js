const fs = require('fs');
const { makeLib, prepIcons, THEME } = require('./lib');
const { applyTheme } = require('./theme');
const PARTS = ['p00', 'p01', 'p02', 'p03', 'p04', 'p05', 'p06', 'p07', 'p08', 'p09', 'p10', 'p11', 'p12'].filter((p) => fs.existsSync(p + '.js'));
// usage: node build.js [out.pptx] [--ids-only] [--ids-out <file>]
//   --ids-only  collect the slide IDs and write the ID file, without writing the PPTX
//   --ids-out   where to write the ID file (default: slide_ids.json next to this script)
const args = process.argv.slice(2);
const flag = (k) => { const i = args.indexOf(k); if (i < 0) return null; args.splice(i, 1); return true; };
const opt = (k) => { const i = args.indexOf(k); if (i < 0) return null; const v = args[i + 1]; args.splice(i, 2); return v; };
const idsOnly = flag('--ids-only');
const idsOut = opt('--ids-out') || require('path').join(__dirname, 'slide_ids.json');
(async () => {
  const src = ['lib.js', ...PARTS.map((p) => p + '.js')].map((f) => fs.readFileSync(f, 'utf8')).join('\n');
  const names = [...new Set(src.match(/'Md[A-Za-z]+'/g).map((s) => s.slice(1, -1)))];
  await prepIcons(names);
  const L = makeLib();
  PARTS.forEach((p) => { L.part = p; require('./' + p)(L); });
  fs.writeFileSync(idsOut, JSON.stringify(L.slideIds, null, 1) + '\n', 'utf8');
  console.log('slide ids', L.slideIds.length, '->', idsOut);
  if (idsOnly) return;
  const out = args[0] || 'JWT_クレーム設計ガイド.pptx';
  await L.pres.writeFile({ fileName: out });
  await applyTheme(out, THEME);
  console.log('wrote', out);
})().catch((e) => { console.error(e); process.exit(1); });
