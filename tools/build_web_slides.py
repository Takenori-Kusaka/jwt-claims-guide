# -*- coding: utf-8 -*-
"""Build a static web-slide viewer (GitHub Pages: /docs) from exported slide PNGs and the PPTX speaker notes."""
import os, sys, json, html, glob, csv, re
from PIL import Image
from pptx import Presentation

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = 'https://github.com/Takenori-Kusaka/jwt-claims-guide'
ID_RE = re.compile(r'^p\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*$')

def load_slide_ids(slides):
  """Read deck/slide_ids.json (written by `node build.js`) and check that it matches the PPTX slide by slide."""
  ids = json.load(open(os.path.join(ROOT, 'deck', 'slide_ids.json'), encoding='utf-8'))
  if len(ids) != len(slides):
      sys.exit(f'deck/slide_ids.json has {len(ids)} ids but the PPTX has {len(slides)} slides: rebuild the deck (cd deck && node build.js)')
  seen = set()
  norm = lambda t: re.sub(r'\s+', '', t)
  for x, d in zip(ids, slides):
      if x['n'] != d['n'] or not ID_RE.match(x['id']) or x['id'] in seen:
          sys.exit(f'bad or duplicate slide id at slide {d["n"]}: {x}')
      seen.add(x['id'])
      # the deck-side title must appear on the PPTX slide, so a stale ID file cannot silently shift the IDs
      if norm(x['title']) not in norm(d['text']):
          sys.exit(f'slide {d["n"]}: title of {x["id"]} ({x["title"]!r}) is not on the PPTX slide; deck/slide_ids.json is out of date')
  return ids

def build(pptx_name, docs_rel, title, lead, og_desc, other, guide=''):
  # guide: a block of links shown in the page frame, above the table of contents and again after the last slide
  # (the way from the slides to the templates and the editor). The slides themselves are not touched.
  PPTX = os.path.join(ROOT, 'slides', pptx_name)
  DOCS = os.path.join(ROOT, 'docs', docs_rel); SL = os.path.join(DOCS, 'slides')
  base = pptx_name[:-5]

  # 1) PNG -> WebP (smaller pages)
  imgs = sorted(glob.glob(os.path.join(SL, 's*.png')))
  for p in imgs:
      Image.open(p).convert('RGB').save(p[:-4] + '.webp', 'WEBP', quality=82, method=6); os.remove(p)

  # 2) text and notes per slide
  prs = Presentation(PPTX); slides = []
  for i, s in enumerate(prs.slides, 1):
      texts = []
      for sh in s.shapes:
          if sh.has_text_frame and sh.text_frame.text.strip(): texts.append(sh.text_frame.text.strip())
          if getattr(sh, 'has_table', False) and sh.has_table:
              for row in sh.table.rows: texts.append(' | '.join(c.text for c in row.cells))
      stitle = texts[0].split('\n')[0] if texts else f'Slide {i}'
      for t in texts:
          if s.shapes.title is not None and s.shapes.title.has_text_frame and s.shapes.title.text_frame.text.strip():
              stitle = s.shapes.title.text_frame.text.strip(); break
      notes = s.notes_slide.notes_text_frame.text.strip() if s.has_notes_slide else ''
      slides.append(dict(n=i, title=stitle, text='\n'.join(texts), notes=notes))

  # 2b) stable slide IDs (issue #15), recorded by deck/build.js in slide order
  ids = load_slide_ids(slides)
  slides = [dict(n=d['n'], id=x['id'], title=d['title'], text=d['text'], notes=d['notes']) for d, x in zip(slides, ids)]
  with open(os.path.join(DOCS, 'slide_ids.csv'), 'w', encoding='utf-8', newline='') as f:
      # title = the title shown in the web viewer and docs/slides.json (the PPTX title placeholder; "PART 1"
      # for a part divider); source_title = the title given in deck/p*.js, as in deck/slide_ids.json
      w = csv.writer(f, lineterminator='\n'); w.writerow(['n', 'id', 'title', 'source_title'])
      for d, x in zip(slides, ids): w.writerow([d['n'], d['id'], d['title'], x['title']])
  json.dump(slides, open(os.path.join(DOCS, 'slides.json'), 'w', encoding='utf-8'), ensure_ascii=False)

  # 3) viewer page
  items = '\n'.join(
      f'<section class="slide" id="s{d["n"]}" data-n="{d["n"]}" data-id="{d["id"]}"><span class="anc" id="{d["id"]}"></span><img src="slides/s{d["n"]:03d}.webp" loading="{"eager" if d["n"] <= 2 else "lazy"}" width="1920" height="1080" alt="{html.escape(d["title"])}">'
      f'<details><summary>スライド {d["n"]} のテキストと解説（ID: <code>{d["id"]}</code>）</summary><div class="tx">{html.escape(d["text"])}</div>'
      + (f'<div class="nt"><b>解説</b><p>{html.escape(d["notes"])}</p></div>' if d['notes'] else '') + '</details></section>'
      for d in slides)
  toc = ''.join(f'<li><a href="#{d["id"]}">{d["n"]}. {html.escape(d["title"])}</a></li>' for d in slides)
  page = f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{title}</title>
  <meta name="description" content="{og_desc}">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{og_desc}">
  <meta property="og:image" content="slides/s001.webp">
  <style>
  :root{{--bg:#f4f7f8;--fg:#1a2230;--muted:#5b6872;--card:#fff;--acc:#2c5fa8}}
  @media (prefers-color-scheme:dark){{:root{{--bg:#0f1a20;--fg:#e6edf0;--muted:#9fb0b8;--card:#17252d;--acc:#8fb4ea}}}}
  *{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--fg);font-family:"BIZ UDPGothic","Hiragino Sans","Noto Sans JP",sans-serif;line-height:1.7}}
  header,main,footer{{max-width:1100px;margin:0 auto;padding:16px}}h1{{font-size:1.5rem;margin:.4em 0}}a{{color:var(--acc)}}
  .bar{{position:sticky;top:0;z-index:2;background:var(--bg);display:flex;gap:8px;align-items:center;padding:8px 16px;border-bottom:1px solid #8883}}
  .bar button{{font:inherit;padding:4px 12px;border-radius:6px;border:1px solid #8886;background:var(--card);color:var(--fg);cursor:pointer}}
  .slide{{background:var(--card);border-radius:10px;margin:0 0 20px;box-shadow:0 1px 4px #0002;overflow:hidden}}
  .slide img{{display:block;width:100%;height:auto}}details{{padding:8px 14px}}summary{{cursor:pointer;color:var(--muted)}}
  .tx{{white-space:pre-wrap;font-size:.85rem;color:var(--muted)}}.nt p{{margin:.3em 0;font-size:.95rem}}
  body.present{{overflow:hidden}}body.present header,body.present footer,body.present details{{display:none}}
  body.present main{{max-width:none;padding:0}}body.present .slide{{display:none;margin:0;border-radius:0;box-shadow:none;background:#000}}
  body.present .slide.on{{display:flex;align-items:center;justify-content:center;height:calc(100vh - 49px)}}
  body.present .slide.on img{{max-height:100%;width:auto;max-width:100%}}
  .guide{{background:var(--card);border:1px solid #8884;border-left:4px solid var(--acc);border-radius:8px;padding:10px 16px;margin:12px 0}}
  .guide p{{margin:.2em 0}}.guide ul{{margin:.3em 0;padding-left:1.3em}}
  ol{{columns:2;font-size:.9rem}}@media (max-width:700px){{ol{{columns:1}}}}
  </style></head><body>
  <div class="bar"><button id="mode">プレゼン表示</button><button id="prev" aria-label="前のスライド">←</button><button id="next" aria-label="次のスライド">→</button><span id="pos"></span></div>
  <header><h1>{title}</h1>
  <p>{lead}（全 {len(slides)} 枚）。<a href="{REPO}">GitHub リポジトリ</a>／<a href="{REPO}/raw/main/slides/{base}.pdf">PDF</a>／<a href="{REPO}/raw/main/slides/{base}.pptx">PPTX</a>／{other}</p>
  {guide}
  <details><summary>目次</summary><ol>{toc}</ol></details></header>
  <main>{items}</main>
  <footer>{guide}<p>本資料と実験データは CC BY 4.0、コードは MIT ライセンスです。本資料は生成AI（Claude）を使って作成し、筆者が確認して公開しています。</p></footer>
  <script>
  const S=[...document.querySelectorAll('.slide')];let i=0;const pos=document.getElementById('pos');
  function show(n){{i=Math.max(0,Math.min(S.length-1,n));S.forEach((s,k)=>s.classList.toggle('on',k===i));pos.textContent=(i+1)+' / '+S.length;
   if(!document.body.classList.contains('present'))S[i].scrollIntoView({{behavior:'smooth'}});history.replaceState(null,'','#'+S[i].dataset.id);}}
  document.getElementById('mode').onclick=()=>{{document.body.classList.toggle('present');show(i);}};
  document.getElementById('prev').onclick=()=>show(i-1);document.getElementById('next').onclick=()=>show(i+1);
  addEventListener('keydown',e=>{{if(['ArrowRight','PageDown',' '].includes(e.key)){{e.preventDefault();show(i+1)}}if(['ArrowLeft','PageUp'].includes(e.key)){{e.preventDefault();show(i-1)}}if(e.key==='Escape')document.body.classList.remove('present')}});
  let x0=null;addEventListener('touchstart',e=>x0=e.touches[0].clientX);addEventListener('touchend',e=>{{if(x0===null)return;const d=e.changedTouches[0].clientX-x0;if(Math.abs(d)>50)show(i+(d<0?1:-1));x0=null}});
  // #<slide id> (stable, e.g. #p04-carry-or-query) or #sNN (slide number, kept for old links)
  // an unknown or malformed hash (e.g. "#%E0") falls back to slide 1 and says so
  let miss='';
  function idx(){{miss='';let h=location.hash.slice(1);if(!h)return 0;try{{h=decodeURIComponent(h)}}catch(e){{}}const k=S.findIndex(s=>s.dataset.id===h);if(k>=0)return k;const m=/^s([0-9]+)$/.exec(h);if(m&&+m[1]>=1&&+m[1]<=S.length)return +m[1]-1;miss=h;return 0;}}
  function note(){{if(miss)pos.textContent+='（#'+miss+' のスライドは見つかりません）';}}
  addEventListener('hashchange',()=>{{const k=idx();if(k!==i||miss)show(k);note();}});
  i=idx();pos.textContent=(i+1)+' / '+S.length;note();S[i]&&S[i].classList.add('on');
  </script></body></html>'''
  open(os.path.join(DOCS, 'index.html'), 'w', encoding='utf-8', newline='\n').write(page)
  open(os.path.join(DOCS, '.nojekyll'), 'w').close()
  print('slides', len(slides), 'size MB', round(sum(os.path.getsize(f) for f in glob.glob(SL + '/*')) / 1e6, 1))

build('JWT_クレーム設計ガイド.pptx', '', 'JWT クレーム設計ガイド ― 組織のあらゆるサービスで共用する独自クレームを、どう設計し、どう流し、どう治めるか',
      '認証認可とマイクロサービスの設計を任された新任のテックリーダーに向けて、JWT の独自クレームの設計・伝搬・検証・ガバナンスを、標準クレームと 4 つの IdP（Entra ID・Keycloak・Auth0/Okta・Cognito）の実際を前提に解説する資料です',
      'クレームはサービス間の契約。既存のクレームの地図、4 つの IdP の実際、独自クレームの設計原則、マイクロサービスの流れ、データ層、期限、機微情報、AI エージェント、ガバナンスを、RFC・NIST・OWASP・デジタル庁の指針と日本語の専門書を根拠に解説',
      '<a href="https://github.com/Takenori-Kusaka/jwt-claims-casestudy">ケーススタディ（実測）</a>／<a href="https://github.com/Takenori-Kusaka/jwt-claims-casestudy/blob/main/catalog/jwt-claims-catalog.xlsx">付録：JWT クレーム一覧（xlsx）</a>／<a href="https://takenori-kusaka.github.io/agentops-reliability-guide/">関連：AgentOps と Agent Reliability 実践ガイド</a>',
      guide='<nav class="guide" aria-label="設計書を書く"><p><b>このガイドに沿って設計書を書く：テンプレートとエディター</b></p><ul>'
            '<li><a href="claims/">設計書のエディター</a>：ブラウザで設計書を書き、その場で検査し、レビューする。記入例も開ける。開いたファイルは外部に送信しない</li>'
            f'<li><a href="{REPO}/blob/main/templates/GETTING_STARTED.md">テンプレートの始め方</a>：空の設計書を作り、最初の検査を通すまでの手順（<a href="{REPO}/tree/main/templates">テンプレート一式</a>）</li>'
            f'<li><a href="{REPO}#readme">リポジトリの案内</a>：読む・書く・レビューする・検査する、の 4 つの入口</li>'
            '</ul></nav>')
