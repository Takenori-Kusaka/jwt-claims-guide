# -*- coding: utf-8 -*-
"""Run the runtime tests of #8 and write the run log.

  python tools/runtime_tests/run.py --env offline [--log research/runtime/offline.json]
  python tools/runtime_tests/run.py --env live    [--log research/runtime/live-YYYY-MM-DD.json] [--select negative_tests#rt-reuse ...]

offline: crafted tokens and the reference receivers (CI runs this). live: Keycloak 26.8.0 + Postgres 16 in WSL Docker under
the compose project jcg-issue8-runtime (ports 38080 / 35432), removed at the end. Exit status 1 if a case fails.
The log holds the decoded claims of test users and the observed results, never a raw token, key or password.
"""
import argparse
import datetime
import json
import os
import platform
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import harness  # noqa: E402


def environment():
    import cryptography
    import yaml
    return {'python': platform.python_version(), 'os': platform.platform(), 'cryptography': cryptography.__version__, 'pyyaml': yaml.__version__}


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--env', choices=('offline', 'live'), default='offline')
    ap.add_argument('--log', help='write the JSON log here (and a .md summary next to it)')
    ap.add_argument('--select', nargs='*', help='run only these test IDs (<file>#<anchor>)')
    a = ap.parse_args(argv)
    if a.env == 'offline':
        import cases_offline as mod
    else:
        import cases_live as mod
    cases = [c for c in harness.CASES if c['env'] == a.env]
    holder = {}

    def factory():
        holder['ctx'] = mod.new_ctx()
        return holder['ctx']
    started = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
    teardown = None
    try:
        results = harness.execute(cases, factory, set(a.select) if a.select else None)
    finally:
        ctx = holder.get('ctx')
        if ctx is not None and hasattr(ctx, 'close'):
            teardown = ctx.close()
    log = {'run': {'env': a.env, 'started_utc': started, 'environment': environment()}, 'results': results}
    if a.env == 'live' and holder.get('ctx'):
        log['run']['live'] = dict(holder['ctx'].env.versions(), keycloak_boot_s=holder['ctx'].boot_s,
                                  containers_removed=teardown is not None)
    lines = harness.summary_lines(results)
    print('\n'.join(lines))
    if a.log:
        os.makedirs(os.path.dirname(os.path.abspath(a.log)), exist_ok=True)
        json.dump(log, open(a.log, 'w', encoding='utf-8', newline='\n'), ensure_ascii=False, indent=1, default=str)
        md = os.path.splitext(a.log)[0] + '.md'
        open(md, 'w', encoding='utf-8', newline='\n').write(render_md(log))
    return 0 if results and all(r['ok'] for r in results) else 1


def render_md(log):
    run = log['run']
    out = [f"# 実行テストの記録（#8、env={run['env']}）", '',
           f"- 開始（UTC）：{run['started_utc']}", f"- 環境：{json.dumps(run['environment'], ensure_ascii=False)}"]
    if 'live' in run:
        out.append(f"- コンテナ：{json.dumps(run['live'], ensure_ascii=False)}")
    out += ['- 生のトークン・鍵・パスワードは記録しない。試験用の利用者の復号したクレームだけを記録する', '',
            '| テスト | 結果 | 確かめた数 | 要件 | lint | 期待する結果 |', '| --- | --- | --- | --- | --- | --- |']
    for r in log['results']:
        n_ok = sum(k['ok'] for k in r['checks'])
        out.append(f"| `{r['id']}` | {'PASS' if r['ok'] else 'FAIL'} | {n_ok}/{len(r['checks'])} | {'・'.join(r['requirements']) or '—'} | "
                   f"{'・'.join(r['lint']) or '—'} | {r['expected']} |")
    out.append('')
    for r in log['results']:
        out += [f"## `{r['id']}`（{r['title']}）", '', '| 確かめたこと | 期待 | 観測 | 判定 |', '| --- | --- | --- | --- |']
        for k in r['checks']:
            obs = json.dumps(k['observed'], ensure_ascii=False, default=str) if not isinstance(k['observed'], str) else k['observed']
            obs = obs.replace('|', '\\|').replace('\n', ' ')
            out.append(f"| {k['name']} | {k['expected']} | {obs[:400]} | {'OK' if k['ok'] else 'NG'} |")
        for n in r['notes']:
            out.append(f'\n- 注：{n}')
        if r['error']:
            out.append(f"\n```\n{r['error']}\n```")
        out.append('')
    return '\n'.join(out)


if __name__ == '__main__':
    sys.exit(main())
