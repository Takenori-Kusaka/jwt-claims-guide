// Entry of docs/claims/vendor/editor-libs.js (#49): the libraries the design editor uses, exposed as window.EditorLibs.
// Built by build.mjs (esbuild, one IIFE file, no eval): the editor page loads it with <script src> from the same origin.
export { EditorState, EditorSelection, StateEffect, StateField, Compartment, RangeSetBuilder } from '@codemirror/state';
export { EditorView, keymap, lineNumbers, highlightActiveLine, highlightActiveLineGutter, drawSelection, Decoration,
  ViewPlugin, placeholder } from '@codemirror/view';
export { defaultKeymap, history, historyKeymap, indentMore, indentLess } from '@codemirror/commands';
export { foldGutter, foldKeymap, foldAll, unfoldAll, syntaxHighlighting, defaultHighlightStyle, indentOnInput,
  bracketMatching, indentUnit } from '@codemirror/language';
export { search, searchKeymap, highlightSelectionMatches, openSearchPanel } from '@codemirror/search';
export { linter, lintGutter, setDiagnostics, lintKeymap, forEachDiagnostic, nextDiagnostic } from '@codemirror/lint';
export { yaml as yamlLanguage } from '@codemirror/lang-yaml';
export { parseDocument, LineCounter, isMap, isSeq, isScalar, isPair, isAlias } from 'yaml';
export { Validator } from '@cfworker/json-schema';
export { zipSync, unzipSync, strToU8, strFromU8 } from 'fflate';
