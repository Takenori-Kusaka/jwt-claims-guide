"""Small link checker for Markdown files (external + relative links).

Usage: python linkcheck.py <dir> <out.txt> [manual.tsv]
- Collects Markdown links and bare URLs (inline code is skipped: identifiers, not links).
- External: HEAD, then GET on failure. Generic browser-like User-Agent, timeout 30s.
- 429/5xx/timeouts: sequential retries with back-off.
- doi.org: when the publisher blocks automated access (403), the DOI is checked with the
  doi.org handle API (responseCode 1 = registered).
- manual.tsv (url<TAB>evidence): URLs that refuse automated clients from this network,
  confirmed by another means (browser, search index). Reported separately, not as OK.
"""
import sys, re, json, time, pathlib, urllib.request, urllib.error, urllib.parse, ssl, concurrent.futures, datetime

root = pathlib.Path(sys.argv[1])
out = pathlib.Path(sys.argv[2])
manual = {}
if len(sys.argv) > 3:
    for l in open(sys.argv[3], encoding="utf-8"):
        if l.strip() and not l.startswith("#"):
            u, ev = l.rstrip("\n").split("\t", 1)
            manual[u] = ev

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
HDR = {"User-Agent": UA, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Accept-Language": "en-US,en;q=0.9"}
LINK = re.compile(r"\]\((<[^>]+>|[^)\s]+)\)|(?<![(\[<])(https?://[^\s)<>\]|`]+)")
ctx = ssl.create_default_context()

links = {}
for f in sorted(root.rglob("*.md")):
    for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
        line = re.sub(r"`[^`]*`", "", line)
        for m in LINK.finditer(line):
            u = (m.group(1) or m.group(2)).strip("<>").rstrip(".,;、。")
            links.setdefault((f, u), set()).add(i)

def fetch(url, method):
    req = urllib.request.Request(url, method=method, headers=HDR)
    with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
        return r.status

def check(url):
    last = None
    for method in ("HEAD", "GET"):
        try:
            return str(fetch(url, method)), method
        except urllib.error.HTTPError as e:
            last = (str(e.code), method)
        except Exception as e:
            last = ("ERR " + type(e).__name__, method)
    return last

def doi_registered(url):
    doi = urllib.parse.urlparse(url).path.lstrip("/")
    try:
        with urllib.request.urlopen("https://doi.org/api/handles/" + doi, timeout=30, context=ctx) as r:
            return json.load(r).get("responseCode") == 1
    except Exception:
        return False

ext = sorted({u for (_, u) in links if u.startswith("http")})
res = {}
with concurrent.futures.ThreadPoolExecutor(10) as ex:
    for u, r in zip(ext, ex.map(check, ext)):
        res[u] = r
# second pass: sequential retries for rate limits and timeouts
for u in ext:
    st, m = res[u]
    if st == "429" or st.startswith("5") or st.startswith("ERR"):
        for attempt in range(3):
            time.sleep(10 * (attempt + 1))
            st2, m2 = check(u)
            res[u] = (st2, m2)
            if st2 != "429" and not st2.startswith("5") and not st2.startswith("ERR"):
                break

rows = []
for (f, u), lines in sorted(links.items(), key=lambda x: (str(x[0][0]), x[0][1])):
    rel = f.relative_to(root).as_posix()
    ln = ",".join(map(str, sorted(lines)))
    if u.startswith("#") or u.startswith("mailto:"):
        continue
    if u.startswith("http"):
        st, m = res[u]
        if st.startswith("2"):
            cls, note = "OK", f"{st} {m}"
        elif "doi.org/" in u and doi_registered(u):
            cls, note = "OK-DOI", f"{st} {m}; DOI registered (doi.org handle API)"
        elif u in manual:
            cls, note = "OK-MANUAL", f"{st} {m}; {manual[u]}"
        else:
            cls, note = "BROKEN", f"{st} {m}"
    else:
        target = (f.parent / urllib.parse.unquote(u.split("#")[0])).resolve()
        cls, note = ("OK", "file exists") if target.exists() else ("BROKEN", "file missing")
    rows.append((cls, rel, ln, u, note))

count = {}
for r in rows:
    count[r[0]] = count.get(r[0], 0) + 1
with out.open("w", encoding="utf-8", newline="\n") as fh:
    fh.write("# Link check: research/template-design/\n")
    fh.write(f"# date: {datetime.date.today().isoformat()}  tool: tools/linkcheck.py (Python urllib; HEAD then GET, generic UA, 30s timeout, retries on 429/5xx/timeouts)\n")
    fh.write(f"# links (file x url): {len(rows)}  unique external URLs: {len(ext)}  relative links: {sum(1 for r in rows if not r[3].startswith('http'))}\n")
    for k in ("OK", "OK-DOI", "OK-MANUAL", "BROKEN"):
        fh.write(f"# {k}: {count.get(k, 0)}\n")
    fh.write("# OK-DOI: publisher refuses automated clients; DOI confirmed registered.\n")
    fh.write("# OK-MANUAL: site refuses automated clients from this network; existence confirmed by another means (see note).\n\n")
    fh.write("## Not plain OK\n")
    for r in rows:
        if r[0] != "OK":
            fh.write("\t".join(r) + "\n")
    fh.write("\n## All links\n")
    for r in rows:
        fh.write("\t".join(r) + "\n")
print(count)
for r in rows:
    if r[0] == "BROKEN":
        print("\t".join(r))
