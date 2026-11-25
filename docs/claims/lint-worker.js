// claim_lint in the browser (#49). MIT (LICENSE of the repository).
// A classic worker. editor.js starts it from a blob: URL (`importScripts(<this file>)`), so that the worker inherits the
// CSP of the page (a worker loaded from its own http URL would take the CSP of its response headers, which GitHub Pages
// does not set). Everything is loaded from this site: Pyodide and its wheels from vendor/pyodide/ (pinned, sha256 in
// vendor/MANIFEST.json; Pyodide checks the sha256 of each wheel against pyodide-lock.json) and claim_lint with the files
// it reads from data/claim_lint.zip. Nothing is sent: the only requests are GETs of these files (connect-src 'self').
'use strict';
/* global loadPyodide */
// the build id (tools/build_claims_viewer.py, #53): the page compares it with its own, so that a worker of another
// build (a newer file from the server than the page in the cache) is not used
const BUILD_ID = '7eb4b171d5ee';
let ASSETS = {};
// the URL of a file with its content hash (?v=, data/build.js), given by the page
function asset(path) { return ASSETS[path] ? path + '?v=' + ASSETS[path] : path; }
let py = null;
let lintFn = null;

const DRIVER = `
import json, os, shutil, sys, traceback
sys.path.insert(0, '/repo/tools')
sys.dont_write_bytecode = True
from claim_lint import core, render

SAFE = __import__('re').compile(r'^(claims|token_types|hops|catalog_answers)\\.yaml$|^claim_request_[A-Za-z0-9_-]+\\.md$|^design\\.md$')

def lint_design(files_json, design_rel, profile):
    files = json.loads(files_json)
    d = '/repo/' + design_rel
    if os.path.isdir(d):
        shutil.rmtree(d)
    os.makedirs(d)
    for name, text in files.items():
        if SAFE.match(name):
            with open(os.path.join(d, name), 'w', encoding='utf-8', newline='') as f:
                f.write(text)
    doc = os.path.join(d, render.DOC_NAME)
    extra = [doc] if os.path.isfile(doc) else []
    out = {'lint': None, 'bundle': None, 'errors': []}
    try:
        out['lint'] = core.run(d, profile=profile, extra_files=extra)
    except Exception:
        out['errors'].append('claim_lint: ' + traceback.format_exc(limit=3))
    try:
        dd = render.load_design(d)
        out['bundle'] = render.bundle(d, dd, render.build_sections(dd, out['lint']))
    except Exception:
        out['errors'].append('render: ' + traceback.format_exc(limit=3))
    return json.dumps(out, ensure_ascii=False)
`;

async function init(base, assets) {
  const t0 = Date.now();
  ASSETS = assets || {};
  importScripts(base + asset('vendor/pyodide/pyodide.js'));
  py = await loadPyodide({ indexURL: base + 'vendor/pyodide/', stdout: () => {}, stderr: () => {} });
  await py.loadPackage(['pyyaml', 'jsonschema'], { messageCallback: () => {}, errorCallback: (m) => { throw new Error(m); } });
  const res = await fetch(base + asset('data/claim_lint.zip'), { credentials: 'omit', cache: 'no-cache' });
  if (!res.ok) throw new Error('data/claim_lint.zip: HTTP ' + res.status);
  py.unpackArchive(await res.arrayBuffer(), 'zip', { extractDir: '/repo' });
  py.runPython(DRIVER);
  lintFn = py.globals.get('lint_design');
  return { build: BUILD_ID, ms: Date.now() - t0, python: py.runPython('import sys; sys.version.split()[0]'), pyodide: py.version };
}

self.onmessage = async (e) => {
  const m = e.data || {};
  try {
    if (m.type === 'init') {
      const info = await init(m.base, m.assets);
      self.postMessage({ type: 'ready', id: m.id, info });
    } else if (m.type === 'lint') {
      if (!lintFn) throw new Error('not initialised');
      const t0 = Date.now();
      const out = JSON.parse(lintFn(JSON.stringify(m.files), m.designRel, m.profile));
      self.postMessage({ type: 'result', id: m.id, ms: Date.now() - t0, out });
    }
  } catch (err) {
    self.postMessage({ type: 'error', id: m.id, message: String((err && err.message) || err) });
  }
};
