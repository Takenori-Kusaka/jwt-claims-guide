// Build docs/claims/vendor/editor-libs.js and its license file from the pinned packages of package-lock.json (#49).
//   cd tools/claims_editor_vendor && npm ci --ignore-scripts && node build.mjs
// Then run python tools/build_claims_viewer.py (it records the sha256 in docs/claims/vendor/MANIFEST.json).
import { build } from 'esbuild';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const out = path.join(here, '..', '..', 'docs', 'claims', 'vendor');
const lock = JSON.parse(fs.readFileSync(path.join(here, 'package-lock.json'), 'utf8'));

await build({
  entryPoints: [path.join(here, 'entry.mjs')],
  bundle: true,
  format: 'iife',
  globalName: 'EditorLibs',
  target: ['chrome111', 'firefox115', 'safari16'],
  minify: true,
  legalComments: 'none',  // the licenses are in editor-libs.LICENSES.txt
  charset: 'utf8',
  outfile: path.join(out, 'editor-libs.js'),
  banner: { js: '/* editor-libs.js (#49): CodeMirror 6, yaml, @cfworker/json-schema, fflate. Licenses: editor-libs.LICENSES.txt. Built by tools/claims_editor_vendor/build.mjs */' },
});

// license texts of every package in the bundle (production dependencies of the lock file)
const parts = [];
for (const [key, p] of Object.entries(lock.packages).sort()) {
  if (!key || p.dev) continue;
  const dir = path.join(here, key);
  const lic = fs.readdirSync(dir).find((f) => /^(license|licence)(\.(md|txt))?$/i.test(f));
  const name = key.replace(/^node_modules\//, '');
  parts.push(`==== ${name}@${p.version} (${p.license}) ====\n` + (lic ? fs.readFileSync(path.join(dir, lic), 'utf8').replace(/\r\n/g, '\n').trim() : '(no license file in the package; license field: ' + p.license + ')') + '\n');
}
fs.writeFileSync(path.join(out, 'editor-libs.LICENSES.txt'), parts.join('\n'));
console.log('wrote', path.join(out, 'editor-libs.js'), 'and editor-libs.LICENSES.txt');
