// Write the deck colour scheme and fonts into ppt/theme/theme1.xml (pptxgenjs cannot set theme colours itself)
const fs = require('fs');
const JSZip = require('jszip');

async function applyTheme(file, theme) {
  const zip = await JSZip.loadAsync(fs.readFileSync(file));
  const names = Object.keys(zip.files).filter((n) => /^ppt\/theme\/theme\d+\.xml$/.test(n));
  const slot = (k) => `<a:${k}><a:srgbClr val="${theme.colors[k]}"/></a:${k}>`;
  const scheme = `<a:clrScheme name="${theme.name}">${['dk1', 'lt1', 'dk2', 'lt2', 'accent1', 'accent2', 'accent3', 'accent4', 'accent5', 'accent6', 'hlink', 'folHlink'].map(slot).join('')}</a:clrScheme>`;
  for (const n of names) {
    let xml = await zip.file(n).async('string');
    xml = xml.replace(/<a:clrScheme[\s\S]*?<\/a:clrScheme>/, scheme);
    xml = xml.replace(/(<a:majorFont>\s*<a:latin typeface=")[^"]*/, `$1${theme.headFontFace}`)
             .replace(/(<a:minorFont>\s*<a:latin typeface=")[^"]*/, `$1${theme.bodyFontFace}`);
    zip.file(n, xml);
  }
  fs.writeFileSync(file, await zip.generateAsync({ type: 'nodebuffer', compression: 'DEFLATE' }));
}
module.exports = { applyTheme };
