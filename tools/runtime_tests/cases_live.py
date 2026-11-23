# -*- coding: utf-8 -*-
"""Live cases: real Keycloak 26.8.0 tokens and a real Postgres 16, checked by the same reference receivers.

Run locally (not in CI): `python tools/runtime_tests/run.py --env live` (needs WSL Ubuntu-24.04 with Docker; see
templates/runtime/README.md). The containers run under the compose project jcg-issue8-runtime and are removed at the end.
Raw tokens are never written to the log; decoded claims of test users are.
"""
import time

import psycopg

import contract
import db
import narrowing
from harness import case
from jose import decode_unverified
from kc import KC, Env
from scenario_a import DESIGN, Bff, PgStore, SaasApi, load_design
from validator import Reject

DESIGN_ISS = {'t1': 'https://idp.example.com/realms/t1', 't2': 'https://idp.example.com/realms/t2'}
SHORT = {'lifetime': 20, 'skew': 2}    # 300 s and 30 s scaled by 1/15 (lifetime_revocation.md)


class LiveCtx:
    def __init__(self):
        self.env = Env()
        self.boot_s = self.env.up()
        self.issuer_map = {d: f'{KC}/realms/{t}' for t, d in DESIGN_ISS.items()}
        self.jwks = {f'{KC}/realms/{t}': self.env.jwks(t) for t in DESIGN_ISS}
        self.sub = {u: self.env.user_id(r, u) for r, u in (('t1', 'alice'), ('t1', 'carol'), ('t2', 'bob'))}
        self.pg_pw = db.setup(self.env, self.sub['alice'], self.sub['carol'], self.sub['bob'])
        self.pool = db.connect(self.env, 'app_rls', self.pg_pw['app_rls'])   # one pooled connection reused by every request

    def api(self, store=None, overrides=None):
        return SaasApi(self.jwks, store=store, issuer_map=self.issuer_map, overrides=overrides)

    def pg_api(self, overrides=None):
        return self.api(PgStore(self.pool), overrides)

    def at(self, realm, client, user, scope='openid'):
        return self.env.token(realm, client, user, scope)

    def close(self):
        try:
            self.pool.close()
        except Exception:  # noqa: BLE001 - the containers are removed anyway
            pass
        return self.env.down()


def new_ctx():
    return LiveCtx()


def claims_of(tok):
    return decode_unverified(tok)[1]


# ================================================================ scenario A with real Keycloak tokens
@case('golden_tokens#scenario-a-at', env='live', expected='Keycloak 26.8 がレルム t1 で発行した AT を参照の saas-api が受理する', title='実物の見本（シナリオ A）')
def live_golden(ctx, r):
    t = ctx.at('t1', 'saas-web', 'alice')
    api = ctx.pg_api()
    rows = r.accept('alice（t1）の AT で /t1 を一覧（Postgres の RLS つき）', lambda: api.list_invoices(t['access_token'], 't1', time.time()))
    r.add('t1 の行だけ', 'tenant_id がすべて t1', [x['tenant_id'] for x in rows or []], bool(rows) and all(x['tenant_id'] == 't1' for x in rows))
    h, c = decode_unverified(t['access_token'])
    r.add('ヘッダー', 'RS256・at+jwt', {k: h.get(k) for k in ('alg', 'typ')}, h.get('alg') == 'RS256' and h.get('typ') == 'at+jwt')
    r.add('ペイロードのクレーム名（記録）', '台帳の AT の行', sorted(c), True)


@case('negative_tests#typ-wrong', env='live', expected='Keycloak の ID トークンを API に送ると typ-mismatch', title='実物の ID トークン')
def live_idt(ctx, r):
    t = ctx.at('t1', 'saas-web', 'alice')
    h, _ = decode_unverified(t['id_token'])
    r.reject(f'ID トークン（ヘッダーの typ={h.get("typ")!r}）を /t1 に送る', lambda: ctx.api().list_invoices(t['id_token'], 't1', time.time()), 'typ-mismatch')


@case('negative_tests#tenant-mismatch', env='live', expected='実物のトークンで、別テナント・他テナントを名乗るマッパー・配列のテナントを拒否', title='実物のテナントの食い違い')
def live_tenant(ctx, r):
    api, now = ctx.api(), time.time()
    bob = ctx.at('t2', 'saas-web', 'bob')['access_token']
    r.reject('bob（t2）の AT で /t1', lambda: api.list_invoices(bob, 't1', now, {'X-Tenant': 't1'}), 'tenant-path-mismatch')
    rogue = ctx.at('t2', 'rogue-web', 'bob')['access_token']
    r.add('t2 のマッパーが出した tenant_id（記録）', 't1', claims_of(rogue)['https://claims.example.com/'].get('tenant_id'), True)
    r.reject('t2 の管理者のマッパーで tenant_id=t1 にした AT で /t1（ケーススタディ A8）', lambda: api.list_invoices(rogue, 't1', now), 'tenant-iss-mismatch')
    multi = ctx.at('t1', 'saas-multi', 'alice')['access_token']
    r.reject('tenant_id が配列の AT（ケーススタディ A12）', lambda: api.list_invoices(multi, 't1', now), 'claim-type')
    r.accept('bob の AT で /t2（正規）', lambda: api.list_invoices(bob, 't2', now))


@case('negative_tests#missing-required-claim', env='live', expected='軽量アクセストークン（名前空間が落ちる）を missing-claim で拒否', title='実物の軽量アクセストークン')
def live_light(ctx, r):
    t = ctx.at('t1', 'saas-light', 'alice')['access_token']
    r.add('軽量アクセストークンのクレーム名（記録）', '名前空間・aud・sub が無い', sorted(claims_of(t)), 'https://claims.example.com/' not in claims_of(t))
    r.reject('軽量アクセストークンで /t2、X-Tenant: t2（ケーススタディ A11）', lambda: ctx.api().list_invoices(t, 't2', time.time(), {'X-Tenant': 't2'}),
             ('missing-claim', 'aud-mismatch'))


@case('negative_tests#untrusted-key', env='live', expected='レルム t1 の署名鍵は t2 の JWKS に無い（テナント単位の鍵）', title='実物の鍵の分離')
def live_keys(ctx, r):
    k1 = {k['kid'] for k in ctx.env.jwks('t1')['keys']}
    k2 = {k['kid'] for k in ctx.env.jwks('t2')['keys']}
    kid = decode_unverified(ctx.at('t1', 'saas-web', 'alice')['access_token'])[0]['kid']
    r.add('t1 の AT の kid', 't1 の JWKS にあり、t2 の JWKS に無い', {'in_t1': kid in k1, 'in_t2': kid in k2}, kid in k1 and kid not in k2)
    r.add('t1 と t2 の JWKS の共通の kid', '0 件', sorted(k1 & k2), not (k1 & k2))


@case('negative_tests#bola-other-owner', env='live', expected='Postgres で持ち主（owner_sub = sub）を照合し、同じテナントの他人の請求書は not-found', title='実物の BOLA')
def live_bola(ctx, r):
    api, now = ctx.pg_api(), time.time()
    t = ctx.at('t1', 'saas-web', 'alice')['access_token']
    r.accept('alice が自分の請求書 2', lambda: api.get_invoice(t, 't1', 2, now))
    r.reject('alice が carol の請求書 3（同じ t1）', lambda: api.get_invoice(t, 't1', 3, now), 'not-found')
    r.reject('alice が t2 の請求書 1', lambda: api.get_invoice(t, 't1', 1, now), 'not-found')


@case('consumer_contract#issued-claims-present', env='live', expected='実物の AT に、台帳で AT に載ると宣言した採用の独自クレームが全部ある', title='実物の黙った欠落')
def live_present(ctx, r):
    _, claims = load_design(DESIGN)
    c = claims_of(ctx.at('t1', 'saas-web', 'alice')['access_token'])
    m = contract.issued_claims_missing(c, list(claims.values()), 'AT')
    r.add('saas-web の AT', '欠落 0', m, not m)
    c = claims_of(ctx.at('t1', 'saas-light', 'alice')['access_token'])
    m = contract.issued_claims_missing(c, list(claims.values()), 'AT')
    r.add('saas-light（軽量アクセストークン）の AT', '欠落を検出', m, bool(m))


@case('consumer_contract#type-shape-match', env='live', expected='実物の AT が issuer 適合のスキーマに合う', title='実物の型と形')
def live_shape(ctx, r):
    import os
    c = claims_of(ctx.at('t1', 'saas-web', 'alice')['access_token'])
    c['iss'] = DESIGN_ISS['t1']  # the schema does not pin iss; kept for the record
    e = contract.schema_errors(c, os.path.join(DESIGN, 'schemas', 'AT.issuer.schema.json'))
    r.add('saas-web の AT と AT.issuer.schema.json', 'スキーマの誤り 0', e, not e)


# ================================================================ exchange (corp realm, the casestudy measurement)
AUD_SCOPES = {'aud-orders': 'orders', 'aud-invoices': 'invoices', 'aud-mcp': 'mcp-tools'}
DELAY = 3
KC_HOP = {'aud_replacement': True, 'aud': ['invoices']}   # mcp-tools exchanges for invoices only (the hop of the measurement)


@case('negative_tests#exchange-narrowing', env='live', expected='Keycloak 26.8 の交換で、元のトークンに無い orders 宛てが出ることを再現し、検査が指摘する。invoices だけへの交換は aud・scope・独自クレームの指摘 0、exp の延長は指摘する',
      title='交換で絞られているか（Keycloak 26.8）')
def live_exchange(ctx, r):
    sub = ctx.env.token('corp', 'portal', 'carol', 'openid aud-mcp')['access_token']
    sc = claims_of(sub)
    time.sleep(DELAY)  # the tool exchanges a few seconds after the user's token was issued, as in a real call chain
    keep = ('aud', 'scope', 'exp', 'iat', 'azp', 'act', 'https://claims.example.com/')
    r.add('元のトークン（subject_token）', '記録', {k: sc.get(k) for k in keep}, True)
    probes = {'narrow_to_invoices': dict(audience='invoices', scope='aud-invoices'), 'audience_not_in_scope': dict(audience='invoices'),
              'audience_not_configured': dict(audience='orders-admin'), 'scope_not_granted': dict(scope='aud-orders'), 'no_audience_no_scope': {}}
    out = {}
    for name, kw in probes.items():
        st, j = ctx.env.exchange('corp', 'mcp-tools', sub, **kw)
        dc = claims_of(j['access_token']) if st == 200 else {}
        out[name] = (st, dc, j.get('error_description') if st != 200 else None)
        f = narrowing.check(sc, dc, KC_HOP, audience_scopes=AUD_SCOPES) if st == 200 else []
        r.add(f'交換 {name}（{kw}）', '記録', {'status': st, 'aud': dc.get('aud'), 'scope': dc.get('scope'), 'has_act': 'act' in dc,
                                              'exp_minus_subject_exp': (dc['exp'] - sc['exp']) if dc else None, 'error': out[name][2], 'findings': f}, True)
    st, dc, _ = out['scope_not_granted']
    f = narrowing.check(sc, dc, KC_HOP, audience_scopes=AUD_SCOPES)
    r.add('ケーススタディと同じ条件（scope=aud-orders）で orders 宛てが出る', 'aud に orders を含む（再現）', dc.get('aud'), 'orders' in (dc.get('aud') or []))
    r.add('その交換を検査が「上流を超えた」と指摘する', '指摘あり', f, any('orders' in x for x in f))
    st, dc, _ = out['narrow_to_invoices']
    f = [x for x in narrowing.check(sc, dc, KC_HOP, audience_scopes=AUD_SCOPES) if not x.startswith('exp')]
    r.add('invoices だけへの交換（aud・scope・独自クレーム）', '指摘 0', f, not f)
    fe = [x for x in narrowing.check(sc, dc, KC_HOP, audience_scopes=AUD_SCOPES) if x.startswith('exp')]
    r.add(f'invoices だけへの交換の exp（元のトークンの {DELAY} 秒後に交換）', '寿命の延長を指摘する（交換の時刻から 300 秒の新しい exp）',
          {'exp_minus_subject_exp': dc['exp'] - sc['exp'], 'findings': fe}, bool(fe) and dc['exp'] - sc['exp'] >= DELAY - 1)
    r.add('元のトークンに act が無く、交換の結果にも act が無い（標準の交換 V2 の既定）', 'act なし', 'act' in dc, 'act' not in dc)


@case('negative_tests#disabled-subject-exchange', env='live', expected='無効にした利用者のトークンを交換しても新しいトークンが出ない', title='無効にした利用者の交換')
def live_disabled_exchange(ctx, r):
    sub = ctx.env.token('corp', 'portal', 'dave', 'openid aud-mcp')['access_token']
    st, _ = ctx.env.exchange('corp', 'mcp-tools', sub, audience='invoices', scope='aud-invoices')
    r.add('無効にする前の交換', '200', st, st == 200)
    ctx.env.set_user('corp', 'dave', enabled=False)
    try:
        st, j = ctx.env.exchange('corp', 'mcp-tools', sub, audience='invoices', scope='aud-invoices')
        r.add('dave を無効にした後、同じ subject_token で交換', '400 番台（トークンが出ない）', {'status': st, 'error': j.get('error'), 'description': j.get('error_description')},
              400 <= st < 500 and 'access_token' not in j)
    finally:
        ctx.env.set_user('corp', 'dave', enabled=True)


# ================================================================ lifetime and revocation (shortened lifetime, lifetime_revocation.md)
def _short_api(ctx):
    return ctx.pg_api(overrides={'max_lifetime': SHORT['lifetime'], 'max_clock_skew': SHORT['skew']})


def _drive(ctx, api, bff, tenant, t_revoke, until, on_tick=None, step=1.0):
    """Call the API through the BFF every `step` seconds until `until` (monotonic deadline); return the event list."""
    events = []
    while time.time() < until:
        now = time.time()
        try:
            rows = bff.call(api, tenant, now, issued_at=bff.issued or now)
            events.append((round(now - t_revoke, 2), 'ok', len(rows)))
            if on_tick:
                on_tick(now, events)
        except Reject as e:
            events.append((round(now - t_revoke, 2), e.code, e.detail[:80]))
            if e.code == 'bff-session-ended':
                break
        time.sleep(step)
    return events


@case('negative_tests#revoked-token-rejected', env='live', expected='IdP 側でセッションを消した・利用者を無効にした後、BFF の次のリフレッシュが失敗して BFF のセッションが終わる（縮めた上限 22 秒以内）。盗まれた AT も exp＋ずれの後は拒否',
      title='IdP 側の失効と BFF のセッション')
def live_revoked(ctx, r):
    old = ctx.env.set_realm('t1', accessTokenLifespan=SHORT['lifetime'])
    bound = SHORT['lifetime'] + SHORT['skew']
    try:
        for how in ('admin_logout', 'user_disabled'):
            api = _short_api(ctx)
            tr = ctx.at('t1', 'saas-web', 'alice')
            t_issue = time.time()
            bff = Bff(tr, lambda rt: ctx.env.refresh('t1', 'saas-web', rt), SHORT['lifetime'])
            bff.issued = t_issue
            time.sleep(3)
            if how == 'admin_logout':
                ctx.env.admin('POST', f"t1/users/{ctx.sub['alice']}/logout")
            else:
                ctx.env.set_user('t1', 'alice', enabled=False)
            t_rev = time.time()
            stolen = tr['access_token']
            t_use = time.time()   # right after the revocation, before the AT's exp (issued 3 s earlier, lifetime 20 s)
            r.accept(f'{how}：取り消しの直後（発行から {t_use - t_issue:.1f} 秒）に、盗まれた AT（BFF の外の写し）を使う＝exp_only の残り',
                     lambda: api.list_invoices(stolen, 't1', t_use))
            ev = _drive(ctx, api, bff, 't1', t_rev, t_rev + bound + 10)
            end = next((e[0] for e in ev if e[1] == 'bff-session-ended'), None)
            r.add(f'{how}：取り消しから BFF のセッションが終わるまで', f'{bound} 秒以内', {'seconds': end, 'events': ev[-4:]}, end is not None and end <= bound)
            wait = t_issue + bound + 1 - time.time()
            if wait > 0:
                time.sleep(wait)
            r.reject(f'{how}：盗まれた AT を発行から {bound + 1} 秒後に使う', lambda: api.list_invoices(stolen, 't1', time.time()), 'expired')
            if how == 'user_disabled':
                ctx.env.set_user('t1', 'alice', enabled=True)
    finally:
        ctx.env.set_realm('t1', accessTokenLifespan=old['accessTokenLifespan'])
        ctx.env.set_user('t1', 'alice', enabled=True)


@case('negative_tests#revocation-latency', env='live', expected='ロールの剥奪は縮めた上限（22 秒）以内に新しい AT に反映。テナントの停止は次の要求で拒否（0 秒、AT の exp を待たない）',
      title='剥奪から拒否までの時間（Keycloak・Postgres）')
def live_latency(ctx, r):
    old = ctx.env.set_realm('t1', accessTokenLifespan=SHORT['lifetime'])
    bound = SHORT['lifetime'] + SHORT['skew']
    try:
        api = _short_api(ctx)
        tr = ctx.at('t1', 'saas-web', 'alice')
        bff = Bff(tr, lambda rt: ctx.env.refresh('t1', 'saas-web', rt), SHORT['lifetime'])
        bff.issued = time.time()
        time.sleep(2)
        ctx.env.realm_role('t1', 'alice', 'approver', add=False)
        t_rev = time.time()
        seen = {}

        def tick(now, events):
            ctx_ = api.authorize(bff.at, 't1', now)
            if 'approver' not in ctx_['roles'] and 'gone' not in seen:
                seen['gone'] = round(now - t_rev, 2)
        _drive(ctx, api, bff, 't1', t_rev, t_rev + bound + 8, on_tick=tick)
        r.add('approver を外してから、API が見るロールから approver が消えるまで', f'{bound} 秒以内（本番の値では 330 秒）', seen.get('gone'),
              seen.get('gone') is not None and seen['gone'] <= bound)
        ctx.env.realm_role('t1', 'alice', 'approver', add=True)
        t = ctx.at('t1', 'saas-web', 'alice')['access_token']
        r.accept('停止の前の要求', lambda: api.list_invoices(t, 't1', time.time()))
        db.set_tenant_status(ctx.env, 't1', 'suspended')
        t0 = time.time()
        r.reject('tenants.status を suspended にした直後の要求（同じ AT）', lambda: api.list_invoices(t, 't1', time.time()), 'tenant-suspended')
        r.add('停止から拒否までの時間', '次の要求（AT の exp を待たない）', f'{(time.time() - t0) * 1000:.1f} ms', True)
    finally:
        db.set_tenant_status(ctx.env, 't1', 'active')
        ctx.env.set_realm('t1', accessTokenLifespan=old['accessTokenLifespan'])
        try:
            ctx.env.realm_role('t1', 'alice', 'approver', add=True)
        except Exception:  # noqa: BLE001 - already granted
            pass


@case('negative_tests#rt-reuse', env='live', expected='ローテーション後の古い RT は拒否される。系列の新しい RT が失効するか（再利用の検知）を記録する', title='RT の再提示')
def live_rt_reuse(ctx, r):
    tr = ctx.at('t1', 'saas-web', 'alice')
    rt1 = tr['refresh_token']
    rt2 = ctx.env.refresh('t1', 'saas-web', rt1)['refresh_token']
    try:
        ctx.env.refresh('t1', 'saas-web', rt1)
        obs = 'accepted'
    except RuntimeError as e:
        obs = str(e)
    r.add('使い終えた RT1 を再提示', '拒否（invalid_grant）', obs, obs != 'accepted')
    try:
        ctx.env.refresh('t1', 'saas-web', rt2)
        fam = 'RT2 は有効なまま（系列は失効しない）'
    except RuntimeError as e:
        fam = f'RT2 も失効（{e}）'
    r.add('再提示の後の、系列の新しい RT2', 'RT2 も失効する（p08-rotation.R3）', fam, fam.startswith('RT2 も失効'))
    r.note('シナリオ A の token_types.yaml は RT の reuse_detection を unverified としている。この観測（Keycloak 26.8.0、refreshTokenMaxReuse 0）で失効を確かめた')


# ================================================================ Postgres: context per transaction, RLS bypass actors
@case('negative_tests#pool-context-leak', env='live', expected='文脈はトランザクションごとに set_config(…, true) で設定し、コミットで消える。SET LOCAL はパラメータにできない。文脈なしは 0 行。セッション単位の設定は漏れる（検出できる）',
      title='接続プールの文脈の残り（A12・A13）')
def live_pool(ctx, r):
    with db.connect(ctx.env, 'app_rls', ctx.pg_pw['app_rls']) as c:
        try:
            with c.transaction():
                c.execute('SET LOCAL app.tenant = %s', ('t1',))
            obs = 'accepted'
        except psycopg.Error as e:
            obs = f'{type(e).__name__}: {str(e).splitlines()[0]}'
        r.add('A12：SET LOCAL app.tenant = $1（パラメータ）', 'Postgres がエラーを返す', obs, obs != 'accepted')
        with c.transaction():
            c.execute("SELECT set_config('app.tenant', %s, true)", ('t2',))
            n = c.execute('SELECT count(*) FROM invoices').fetchone()[0]
        r.add("set_config('app.tenant', $1, true) で t2 を設定", 't2 の 1 行だけ見える', n, n == 1)
        with c.transaction():
            cur = c.execute("SELECT current_setting('app.tenant', true)").fetchone()[0]
            rows = c.execute('SELECT id, tenant_id FROM invoices').fetchall()   # the "forgot the tenant condition" query of casestudy A7
        r.add('A7・A13：次のトランザクション（同じ接続）で文脈を設定し忘れ、条件も書き忘れた集計', '文脈は空、0 行', {'app.tenant': cur, 'rows': rows}, not rows)
        with c.transaction():
            c.execute("SELECT set_config('app.tenant', %s, true)", ('',))
            n = c.execute('SELECT count(*) FROM invoices').fetchone()[0]
        r.add('A13：文脈が空文字', '0 行', n, n == 0)
        c.execute("SELECT set_config('app.tenant', %s, false)", ('t2',))   # the mistake: session-level context
        c.commit()
        with c.transaction():
            rows = c.execute('SELECT id, tenant_id FROM invoices').fetchall()
        r.add('誤り：セッション単位（第 3 引数 false）で t2 を設定した接続を、次の t1 の要求が使う', '漏れを検出（t2 の行が見える）', rows, any(x[1] == 't2' for x in rows))
    api = ctx.pg_api()
    now = time.time()
    api.list_invoices(ctx.at('t2', 'saas-web', 'bob')['access_token'], 't2', now)
    rows = api.list_invoices(ctx.at('t1', 'saas-web', 'alice')['access_token'], 't1', now)
    r.add('参照の saas-api：同じプールの接続で bob（t2）の後に alice（t1）', 't1 の行だけ', [x['tenant_id'] for x in rows], rows and all(x['tenant_id'] == 't1' for x in rows))
    r.note('PgBouncer の transaction pooling は試していない（接続は psycopg の 1 本を使い回した）')


@case('negative_tests#db-context-override', env='live', expected='アプリのロールで RLS をすり抜ける主体（SET ROLE で移れるロールを含む）が 0 件。弱い設定では各項目を検出する。SET ROLE で所有者になれない', title='DB の文脈の上書き・すり抜け（A04）')
def live_override(ctx, r):
    with db.connect(ctx.env, 'app_rls', ctx.pg_pw['app_rls'], autocommit=True) as c:
        hits = db.bypass_actors(c, 'app')
        r.add('A04：設計どおりの app スキーマ（app_rls で照会）', 'すべての項目で 0 件', hits, not any(hits.values()))
        for stmt in ('SET ROLE migrator', 'SET ROLE owner', 'SET SESSION AUTHORIZATION owner'):
            try:
                c.execute(stmt)
                obs = 'accepted'
            except psycopg.Error as e:
                obs = f'{type(e).__name__}: {str(e).splitlines()[0]}'
            r.add(f'{stmt}（所有者・superuser になって RLS を外す）', '権限エラー', obs, obs != 'accepted')
        c.execute("SELECT set_config('app.tenant', 't1', false)")
        leak = c.execute('SELECT count(*) FROM broken.all_invoices').fetchone()[0]
        n = c.execute('SELECT broken.count_all()').fetchone()[0]
        r.add('弱い設定：app_rls が security_invoker の無いビューと SECURITY DEFINER の関数を通して数える（文脈は t1）', 't2 の行まで見える（すり抜けの実例）',
              {'view_rows': leak, 'definer_count': n}, leak == 2 and n == 2)
    with db.connect(ctx.env, 'app_bypass', ctx.pg_pw['app_bypass'], autocommit=True) as c:
        hits = db.bypass_actors(c, 'broken')
        r.add('A04：弱い設定の broken スキーマ（BYPASSRLS のアプリのロールで照会）', '6 項目すべてで検出', hits, all(hits.values()))
