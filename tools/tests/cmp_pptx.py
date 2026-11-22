# -*- coding: utf-8 -*-
"""Compare two PPTX builds part by part, to show that a source change did not alter what is rendered.

  cd deck && node build.js before.pptx      # on the old revision
  cd deck && node build.js after.pptx       # on the new revision
  python tools/tests/cmp_pptx.py before.pptx after.pptx

Prints the parts (files inside the PPTX zip) whose bytes differ. Creation/modification timestamps in
docProps are ignored. For ppt/presentation.xml the random section GUIDs that pptxgenjs generates on
every build are also ignored, so identical sources compare equal. Exit 1 if any part differs.
"""
import re, sys, zipfile


def normalize(name, data):
    if name.startswith('docProps/'):
        data = re.sub(rb'<dcterms:(created|modified)[^<]*</dcterms:\w+>', b'', data)
    if name == 'ppt/presentation.xml':
        data = re.sub(rb'(<p14:section [^>]*?id=")\{[0-9A-Fa-f-]+\}', rb'\1{}', data)
    return data


def main(a, b):
    za, zb = zipfile.ZipFile(a), zipfile.ZipFile(b)
    na, nb = set(za.namelist()), set(zb.namelist())
    diff = sorted(na ^ nb)
    for n in sorted(na & nb):
        if normalize(n, za.read(n)) != normalize(n, zb.read(n)):
            diff.append(n)
    slides = sum(1 for n in na if re.fullmatch(r'ppt/slides/slide\d+\.xml', n))
    print(f'parts: {len(na)} vs {len(nb)}, slides: {slides}')
    print('differing parts:', diff or 'none')
    return 1 if diff else 0


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:3]))
