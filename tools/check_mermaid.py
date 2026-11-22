# -*- coding: utf-8 -*-
"""Render every ```mermaid block in the repository's Markdown with mermaid-cli (mmdc).

GitHub renders mermaid blocks in Markdown and shows "Unable to render rich display" when a
block does not parse (for example a ';' inside a sequenceDiagram message, which mermaid
treats as a statement separator). This script fails if any block fails to render.

Usage: python tools/check_mermaid.py [--mmdc CMD] [paths...]
Default paths: the repository root. Requires Node; mmdc defaults to a pinned npx call.
"""
import argparse
import os
import re
import shlex
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLOCK = re.compile(r"^```mermaid[ \t]*\n(.*?)^```[ \t]*$", re.S | re.M)
SKIP_DIRS = {".git", "node_modules", ".claude", "docs"}
DEFAULT_MMDC = "npx -y -p @mermaid-js/mermaid-cli@11.17.1 mmdc"


def markdown_files(paths):
    for p in paths:
        if os.path.isfile(p):
            if p.endswith(".md"):
                yield p
            continue
        for d, dirs, files in os.walk(p):
            dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
            for f in files:
                if f.endswith(".md"):
                    yield os.path.join(d, f)


def blocks(path):
    text = open(path, encoding="utf-8").read()
    for m in BLOCK.finditer(text):
        line = text.count("\n", 0, m.start()) + 1
        yield line, m.group(1)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mmdc", default=os.environ.get("MMDC", DEFAULT_MMDC))
    ap.add_argument("paths", nargs="*", default=[ROOT])
    a = ap.parse_args(argv)
    cmd = shlex.split(a.mmdc, posix=(os.name != "nt"))
    total = failed = 0
    with tempfile.TemporaryDirectory() as tmp:
        cfg = os.path.join(tmp, "puppeteer.json")
        with open(cfg, "w", encoding="utf-8") as f:
            f.write('{"args": ["--no-sandbox"]}')
        for path in sorted(markdown_files(a.paths)):
            for line, src in blocks(path):
                total += 1
                src_file = os.path.join(tmp, f"d{total}.mmd")
                with open(src_file, "w", encoding="utf-8") as f:
                    f.write(src)
                r = subprocess.run(cmd + ["-q", "-p", cfg, "-i", src_file, "-o", src_file + ".svg"],
                                   capture_output=True, text=True, encoding="utf-8", errors="replace",
                                   shell=(os.name == "nt"))
                try:
                    rel = os.path.relpath(path, ROOT)
                except ValueError:
                    rel = path
                if r.returncode != 0:
                    failed += 1
                    err = next((l for l in r.stderr.splitlines() if "rror" in l), r.stderr.strip()[:200])
                    print(f"NG {rel}:{line}: {err}")
                else:
                    print(f"OK {rel}:{line}")
    print(f"mermaid blocks: {total}, failed: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
