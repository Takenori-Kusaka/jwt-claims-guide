# -*- coding: utf-8 -*-
"""claim_lint (#16, #17, #6).

  python tools/claim_lint DESIGN_DIR [--profile lite|full] [--format table|json] [--json-out FILE]
                                     [--catalog DIR] [--limits FILE] [--lifetime-caps FILE]
  python tools/claim_lint diff --base <git ref> DESIGN_DIR [--format table|json]     (L10: breaking changes)

Exit status: 1 when there is at least one error, 0 otherwise. Rules: tools/claim_lint/RULES.md.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from claim_lint import core  # noqa: E402


def main_diff(argv):
    from claim_lint import diff
    ap = argparse.ArgumentParser(prog='claim_lint diff', description='Report changes that break consumers (L10).')
    ap.add_argument('design_dir')
    ap.add_argument('--base', required=True, help='git ref of the earlier version (e.g. origin/main)')
    ap.add_argument('--format', choices=('table', 'json'), default='table')
    a = ap.parse_args(argv)
    try:
        res = diff.run(a.design_dir, a.base)
    except RuntimeError as e:
        sys.stderr.write(f'claim_lint diff: {e}\n')
        return 2
    text = json.dumps(res, ensure_ascii=False, indent=1) if a.format == 'json' else diff.format_table(res)
    sys.stdout.buffer.write((text + '\n').encode('utf-8'))
    return 1 if res['counts']['error'] else 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == 'diff':
        return main_diff(argv[1:])
    ap = argparse.ArgumentParser(prog='claim_lint', description='Check a claim design (registry, token types, catalogue answers).')
    ap.add_argument('design_dir')
    ap.add_argument('--profile', choices=('lite', 'full'), default='full', help='lite downgrades R2 and R4 to warn (R6 is warn in both)')
    ap.add_argument('--format', choices=('table', 'json'), default='table')
    ap.add_argument('--json-out', help='also write the machine-readable result to this file')
    ap.add_argument('--catalog', help='catalogue directory (default templates/catalog)')
    ap.add_argument('--limits', help='path limits file (default tools/claim_lint/path_limits.yaml)')
    ap.add_argument('--lifetime-caps', help='organization caps of max_lifetime per kind (default tools/claim_lint/lifetime_caps.yaml, L23)')
    ap.add_argument('--also-scan', action='append', default=[], help='extra file scanned for slide:<id> references (e.g. design.md)')
    a = ap.parse_args(argv)
    res = core.run(os.path.abspath(a.design_dir), a.catalog, a.limits, a.profile, extra_files=a.also_scan,
                   caps_path=a.lifetime_caps)
    if a.json_out:
        with open(a.json_out, 'w', encoding='utf-8') as f:
            json.dump(res, f, ensure_ascii=False, indent=1)
    if a.format == 'json':
        sys.stdout.buffer.write((json.dumps(res, ensure_ascii=False, indent=1) + '\n').encode('utf-8'))
    else:
        sys.stdout.buffer.write((core.format_table(res) + '\n').encode('utf-8'))
    return 1 if res['counts']['error'] else 0


if __name__ == '__main__':
    sys.exit(main())
