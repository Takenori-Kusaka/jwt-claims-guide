# -*- coding: utf-8 -*-
"""A plain (unquoted) YAML scalar ends at " #": the rest of the line becomes a comment and the value is silently cut
(e.g. "（L5 の検査は #6）" loads as "（L5 の検査は"). Found while generating the tables of #19. This test scans every
YAML file under templates/ and tools/ for a plain scalar followed on the same line by a comment that looks like the
continuation of the value (no space after '#', as in "#6）" or "#34 の点検"), which an intended comment does not do
("# 1", "# comment"). Quote such a value."""
import glob
import os
import re

import pytest
import yaml

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(TOOLS)
CONTINUATION = re.compile(r'^[ \t]+#(?![ \t#]|$)')


def yaml_files():
    out = []
    for top in ('templates', 'tools'):
        for ext in ('yaml', 'yml'):
            out += glob.glob(os.path.join(ROOT, top, '**', f'*.{ext}'), recursive=True)
    return sorted(out)


def truncated_scalars(text):
    """(line number, value, rest of the line) for plain scalars cut by a ' #' comment that continues the value."""
    lines = text.splitlines()
    out = []

    def walk(node):
        if isinstance(node, yaml.ScalarNode):
            if node.style is None and node.end_mark.line < len(lines):
                rest = lines[node.end_mark.line][node.end_mark.column:]
                if CONTINUATION.match(rest):
                    out.append((node.end_mark.line + 1, node.value, rest.strip()))
        elif isinstance(node, yaml.SequenceNode):
            for x in node.value:
                walk(x)
        elif isinstance(node, yaml.MappingNode):
            for k, v in node.value:
                walk(k)
                walk(v)
    for doc in yaml.compose_all(text, Loader=yaml.SafeLoader):
        if doc is not None:
            walk(doc)
    return out


def test_detector_finds_a_cut_value_and_ignores_intended_comments():
    assert truncated_scalars('a: 値（L5 の検査は #6）\n') == [(1, '値（L5 の検査は', '#6）')]
    assert truncated_scalars('a: x (tracking #16)\n')[0][2] == '#16)'
    assert truncated_scalars('a: 1   # 1\nb: "quoted #6"\nc: x # comment\nd: [a, b] #x\ne: y #\n') == []


@pytest.mark.parametrize('path', yaml_files(), ids=lambda p: os.path.relpath(p, ROOT).replace(os.sep, '/'))
def test_no_plain_scalar_is_cut_by_a_comment(path):
    with open(path, encoding='utf-8') as f:
        text = f.read()
    found = truncated_scalars(text)
    assert not found, '\n'.join(f'{os.path.relpath(path, ROOT)}:{n}: value "{v}" is cut by the comment "{r}" (quote the value)'
                                for n, v, r in found)
