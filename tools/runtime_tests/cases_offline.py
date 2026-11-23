# -*- coding: utf-8 -*-
"""Offline cases: tokens crafted with test keys, checked by the reference receivers written to the designs.

No network, no container. CI runs these (`python tools/runtime_tests/run.py --env offline`).
"""
import copy
import json
import os

import contract
import narrowing
import scenario_b as B
from golden import (DELETE, NOW, NS, A_ISS, Keys, agent_payload, at_header, at_payload, changed, mint_at, mint_sts, mint_txn,
                    task_payload, txn_payload)
from harness import case
from jose import Key, b64e, encode
from scenario_a import DESIGN, MemoryStore, SaasApi, load_design
from validator import Reject

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))


class Ctx:
    def __init__(self):
        self.k = Keys()
        self.fetched = []

    def api(self, store=None, **kw):
        return SaasApi(self.k.jwks_a(), store=store or MemoryStore(), url_fetcher=self.fetched.append, **kw)

    def tok(self, payload=None, tenant='t1', header=None, key=None, **kw):
        return mint_at(self.k, tenant=tenant, payload=payload, header=header, key=key, **kw)


def new_ctx():
    return Ctx()


def _list(api, token, tenant='t1', now=NOW, headers=None):
    return lambda: api.list_invoices(token, tenant, now, headers)


# ================================================================ golden
@case('golden_tokens#scenario-a-at', expected='見本の AT を参照の saas-api が受理する', title='見本のトークン（シナリオ A の AT）')
def golden_a(ctx, r):
    api = ctx.api()
    rows = r.accept('t1 の見本の AT で t1 の請求書を一覧する', _list(api, ctx.tok()))
    r.add('t1 の行だけが返る', 'tenant_id がすべて t1', [x['tenant_id'] for x in rows or []], rows and all(x['tenant_id'] == 't1' for x in rows))
    r.accept('t2 の見本の AT で t2 を一覧する', _list(api, ctx.tok(tenant='t2', payload=at_payload('t2', 'bob-sub')), 't2'))
    r.add('iss に example を含む', 'example を含む', at_payload()['iss'], 'example' in at_payload()['iss'])


@case('golden_tokens#scenario-b-tokens', expected='見本の TXN・TASK_AT を参照の ledger・invoices が受理する', title='見本のトークン（シナリオ B）')
def golden_b(ctx, r):
    led = B.Ledger(ctx.k.jwks_b())
    led.record_start(txn_payload())
    r.accept('TXN を Txn-Token ヘッダーで ledger に送る', lambda: led.accept({'Txn-Token': mint_txn(ctx.k)}, {'operation': 'ledger.read'}, B.ORDERS_ID, NOW))
    inv = B.Invoices(ctx.k.jwks_b(), approvals={'appr-1': 'active'})
    body = {'invoice': 'inv-1', 'amount': 120000, 'creditor': 'JP00-1234-5678'}
    r.accept('TASK_AT で承認どおりの支払い', lambda: inv.pay(mint_sts(ctx.k, task_payload()), body, B.MCP_ID, NOW))
    r.add('iss に example を含む', 'example を含む', [B.TRUST_DOMAIN, 'https://sts.corp.example.com'], True)


# ================================================================ header and algorithm
@case('negative_tests#alg-none', expected='alg-not-allowed で拒否', title='alg=none')
def alg_none(ctx, r):
    api = ctx.api()
    for alg in ('none', 'None', 'NONE'):
        t = encode({'alg': alg, 'typ': 'at+jwt', 'kid': 't1-rs256'}, at_payload())
        r.reject(f'alg={alg}（署名なし）', _list(api, t), 'alg-not-allowed')
    t = encode({'typ': 'at+jwt', 'kid': 't1-rs256'}, at_payload(), key=ctx.k.t1)
    r.reject('alg の欠落', _list(api, t), 'alg-not-allowed')


@case('negative_tests#alg-confusion', expected='alg-not-allowed で拒否（HS256 は許可リストに無い）', title='RS256 と HS256 の混同')
def alg_confusion(ctx, r):
    api = ctx.api()
    pem = ctx.k.t1.public_pem()
    t = encode({'alg': 'HS256', 'typ': 'at+jwt', 'kid': 't1-rs256'}, at_payload(), hmac_secret=pem)
    r.reject('t1 の公開鍵（PEM）を HMAC の鍵にした HS256', _list(api, t), 'alg-not-allowed')
    t = encode({'alg': 'HS256', 'typ': 'at+jwt', 'kid': 't1-rs256'}, at_payload(), hmac_secret=json.dumps(ctx.k.t1.jwk()).encode())
    r.reject('t1 の公開鍵（JWK の JSON）を HMAC の鍵にした HS256', _list(api, t), 'alg-not-allowed')
    es = Key('t1-rs256', 'EC')
    t = encode({'alg': 'ES256', 'typ': 'at+jwt', 'kid': 't1-rs256'}, at_payload(), key=es)
    r.reject('許可リストに無い ES256（kid は t1 の鍵）', _list(api, t), 'alg-not-allowed')


@case('negative_tests#jku-x5u', expected='header-key-param で拒否し、URL を 1 回も取得しない', title='jku・x5u')
def jku_x5u(ctx, r):
    api = ctx.api()
    a = ctx.k.attacker_own
    for p, url in (('jku', 'https://attacker.example.net/jwks.json'), ('x5u', 'https://attacker.example.net/cert.pem')):
        h = {'alg': 'RS256', 'typ': 'at+jwt', 'kid': a.kid, p: url}
        r.reject(f'{p} で攻撃者の鍵の場所を指し、攻撃者の鍵で署名', _list(api, ctx.tok(header=h, key=a)), 'header-key-param')
        h = dict(at_header(ctx.k.t1), **{p: url})
        r.reject(f'正しい t1 の署名に {p} を足したもの', _list(api, ctx.tok(header=h)), 'header-key-param')
    r.add('検証の間に URL を取得した回数', 0, len(ctx.fetched), len(ctx.fetched) == 0)


@case('negative_tests#embedded-jwk', expected='header-key-param で拒否', title='ヘッダーの jwk・x5c')
def embedded_jwk(ctx, r):
    api = ctx.api()
    a = ctx.k.attacker_own
    h = {'alg': 'RS256', 'typ': 'at+jwt', 'kid': a.kid, 'jwk': a.jwk()}
    r.reject('ヘッダーの jwk に自前の公開鍵を入れ、その鍵で署名', _list(api, ctx.tok(header=h, key=a)), 'header-key-param')
    h = {'alg': 'RS256', 'typ': 'at+jwt', 'kid': a.kid, 'x5c': [b64e(b'self-signed certificate (test bytes)')]}
    r.reject('ヘッダーの x5c に自前の証明書を入れたもの', _list(api, ctx.tok(header=h, key=a)), 'header-key-param')


@case('negative_tests#untrusted-key', expected='unknown-kid・bad-signature で拒否。未知の kid での JWKS の取り直しは 300 秒に 1 回まで', title='設定外の鍵・別の発行者の鍵')
def untrusted_key(ctx, r):
    api = ctx.api()
    r.reject('t1 の kid を名乗り、攻撃者の鍵で署名', _list(api, ctx.tok(key=ctx.k.attacker)), 'bad-signature')
    h = at_header(ctx.k.t2)
    r.reject('iss=t1 を t2 の鍵（t2 の kid）で署名（Storm-0558 の型、ケーススタディ A9）', _list(api, ctx.tok(header=h, key=ctx.k.t2)), 'unknown-kid')
    fetches = []

    def fetch(iss):
        fetches.append(iss)
        return ctx.k.jwks_a()[iss]
    api2 = ctx.api(fetch=fetch)
    for n, kid in enumerate(('rotated-1', 'rotated-2', 'rotated-3')):
        h = {'alg': 'RS256', 'typ': 'at+jwt', 'kid': kid}
        r.reject(f'未知の kid {kid}（{n * 10} 秒後）', _list(api2, ctx.tok(header=h, key=ctx.k.attacker_own), now=NOW + n * 10), 'unknown-kid')
    r.add('300 秒の間の JWKS の取り直し', '1 回', f'{len(fetches)} 回', len(fetches) == 1)


@case('negative_tests#iss-mismatch', expected='iss-not-allowed で拒否（完全一致だけを受ける）', title='iss の不一致')
def iss_mismatch(ctx, r):
    api = ctx.api()
    for iss in ('https://idp.example.com/realms/t1/', 'http://idp.example.com/realms/t1', 'https://IDP.example.com/realms/t1',
                'https://idp.example.com/realms/T1', 'https://idp.example.com/realms/t1x', 'https://idp.example.com/realms/t1/../t2',
                'https://idp.example.com/realms/t1 ', 'https://idp.example.com.attacker.example.net/realms/t1', 'https://idp.example.com'):
        r.reject(f'iss={iss!r}（t1 の鍵で正しく署名）', _list(api, ctx.tok(changed(at_payload(), ['iss'], iss))), 'iss-not-allowed')
    r.reject('iss が配列', _list(api, ctx.tok(changed(at_payload(), ['iss'], [A_ISS['t1']]))), 'iss-not-allowed')


@case('negative_tests#aud-wrong', expected='aud-mismatch で拒否。文字列と配列の aud はどちらも受ける', title='aud の誤り')
def aud_wrong(ctx, r):
    api = ctx.api()
    for aud in ('saas-web', 'account', 'https://graph.microsoft.com', ['other-api'], ['saas-web', 'account'], 'saas-api-admin', 'SAAS-API'):
        r.reject(f'aud={aud!r}', _list(api, ctx.tok(changed(at_payload(), ['aud'], aud))), 'aud-mismatch')
    for aud in (7, [], ['saas-api', 7], None):
        r.reject(f'aud の型の誤り {aud!r}', _list(api, ctx.tok(changed(at_payload(), ['aud'], aud))), ('claim-type', 'missing-claim'))
    r.accept('aud が配列 ["saas-api","account"]（正規）', _list(api, ctx.tok(changed(at_payload(), ['aud'], ['saas-api', 'account']))))
    r.accept('aud が文字列 "saas-api"（正規）', _list(api, ctx.tok()))
    led = _ledger(ctx)
    p = changed(txn_payload(), ['aud'], 'https://partner.example.com')
    led.record_start(p)
    r.reject('シナリオ B：Txn-Token の aud が信頼ドメイン（https://corp.example.com）の外', lambda: led.accept(
        {'Txn-Token': mint_txn(ctx.k, p)}, {'operation': 'ledger.read'}, B.ORDERS_ID, NOW), 'aud-mismatch')


@case('negative_tests#typ-wrong', expected='typ-mismatch で拒否。application/at+jwt は受ける', title='typ の誤り')
def typ_wrong(ctx, r):
    api = ctx.api()
    for typ in ('JWT', 'jwt', 'logout+jwt', 'txntoken+jwt', 'dpop+jwt', 'at+JWT+extra', None):
        h = {'alg': 'RS256', 'kid': 't1-rs256'}
        if typ:
            h['typ'] = typ
        r.reject(f'ヘッダーの typ={typ!r}', _list(api, ctx.tok(header=h)), 'typ-mismatch')
    idt = dict(at_payload(), aud='saas-web', typ='ID', nonce='n-1')
    r.reject('ID トークンの形（typ JWT、aud saas-web）を API に送る（ケーススタディ A13）',
             _list(api, ctx.tok(idt, header={'alg': 'RS256', 'typ': 'JWT', 'kid': 't1-rs256'})), 'typ-mismatch')
    r.accept('typ=application/at+jwt（RFC 9068 §2.1 の別の書き方、正規）',
             _list(api, ctx.tok(header={'alg': 'RS256', 'typ': 'application/at+jwt', 'kid': 't1-rs256'})))


@case('negative_tests#expired', expected='expired・lifetime-too-long で拒否。ずれ 30 秒の境界までは受ける', title='期限切れ')
def expired(ctx, r):
    api = ctx.api()
    t = ctx.tok()
    r.accept('exp ちょうど＋30 秒（受け入れの上限 330 秒の境界）', _list(api, t, now=NOW + 330))
    r.reject('exp＋31 秒（発行から 331 秒）', _list(api, t, now=NOW + 331), 'expired')
    r.reject('発行から 400 秒（ケーススタディ A14）', _list(api, t, now=NOW + 400), 'expired')
    p = changed(at_payload(), ['exp'], NOW + 301)
    r.reject('exp − iat = 301 秒（テナントの管理者が寿命を延ばした）', _list(api, ctx.tok(p)), 'lifetime-too-long')
    p = changed(at_payload(), ['exp'], str(NOW + 300))
    r.reject('exp が文字列', _list(api, ctx.tok(p)), 'claim-type')
    p = changed(at_payload(), ['exp'], True)
    r.reject('exp が真偽値', _list(api, ctx.tok(p)), 'claim-type')


@case('negative_tests#nbf-future', expected='not-yet-valid・iat-in-future で拒否。ずれ 30 秒までは受ける', title='nbf が未来・時刻のずれ')
def nbf_future(ctx, r):
    api = ctx.api()
    p = dict(at_payload(), nbf=NOW + 31)
    r.reject('nbf が 31 秒先', _list(api, ctx.tok(p)), 'not-yet-valid')
    p = dict(at_payload(), nbf=NOW + 30)
    r.accept('nbf が 30 秒先（ずれの許容の内側）', _list(api, ctx.tok(p)))
    p = at_payload(now=NOW + 31)
    r.reject('iat が 31 秒先（発行者の時計が進んでいる）', _list(api, ctx.tok(p)), 'iat-in-future')
    p = at_payload(now=NOW + 30)
    r.accept('iat が 30 秒先', _list(api, ctx.tok(p)))


@case('negative_tests#missing-required', expected='missing-claim（iss は iss-not-allowed）で拒否。aud は文字列と配列の両方を受ける', title='必須クレームの欠落')
def missing_required(ctx, r):
    api = ctx.api()
    at = load_design(DESIGN)[0]['AT']
    for name in [c for c in at['required_claims'] if '/.' not in c]:
        r.reject(f'{name} を欠く', _list(api, ctx.tok(changed(at_payload(), [name], DELETE))),
                 'iss-not-allowed' if name == 'iss' else 'missing-claim')
    r.reject('exp が null', _list(api, ctx.tok(changed(at_payload(), ['exp'], None))), 'missing-claim')
    r.accept('aud が配列でも受ける', _list(api, ctx.tok(changed(at_payload(), ['aud'], ['saas-api']))))


@case('negative_tests#missing-required-claim', expected='missing-claim で拒否（fail closed）。roles の欠落は「ロールなし」で受ける', title='必須の独自クレームの欠落')
def missing_required_claim(ctx, r):
    api = ctx.api()
    for name in ('tenant_id', 'user_id', 'v'):
        r.reject(f'名前空間の {name} を欠く（マッパーやフックの打ち切りを模擬）', _list(api, ctx.tok(changed(at_payload(), [NS, name], DELETE))), 'missing-claim')
        r.reject(f'名前空間の {name} が null', _list(api, ctx.tok(changed(at_payload(), [NS, name], None))), 'missing-claim')
    r.reject('名前空間のオブジェクトごと欠く（軽量アクセストークン、ケーススタディ A11）', _list(api, ctx.tok(changed(at_payload(), [NS], DELETE))), 'missing-claim')
    r.reject('同時に X-Tenant: t2 を付けても、ヘッダーで補わない', _list(api, ctx.tok(changed(at_payload(), [NS], DELETE)), 't2', headers={'X-Tenant': 't2'}), 'missing-claim')
    ctx_ = api.authorize(ctx.tok(changed(at_payload(), [NS, 'roles'], DELETE)), 't1', NOW)
    r.add('roles を欠く（on_missing: 既定値）', 'ロールなしで受理', ctx_['roles'], ctx_['roles'] == [])


@case('negative_tests#duplicate-claim', expected='duplicate-member で拒否', title='同名のクレームの重複')
def duplicate_claim(ctx, r):
    api = ctx.api()
    base = json.dumps(at_payload(), separators=(',', ':'))
    raw = base[:-1] + ',"sub":"carol-sub"}'
    r.reject('sub が 2 回（後勝ちのパーサーなら carol になる）', _list(api, encode(at_header(ctx.k.t1), None, key=ctx.k.t1, raw_payload=raw)), 'duplicate-member')
    raw = base.replace('"tenant_id":"t1"', '"tenant_id":"t1","tenant_id":"t2"')
    r.reject('名前空間の中の tenant_id が 2 回', _list(api, encode(at_header(ctx.k.t1), None, key=ctx.k.t1, raw_payload=raw)), 'duplicate-member')
    raw = base[:-1] + ',"https://claims.example.com/":{"tenant_id":"t2"}}'
    r.reject('名前空間のオブジェクトが 2 回', _list(api, encode(at_header(ctx.k.t1), None, key=ctx.k.t1, raw_payload=raw)), 'duplicate-member')
    r.reject('ヘッダーの alg が 2 回', _list(api, encode('{"alg":"none","alg":"RS256","typ":"at+jwt","kid":"t1-rs256"}', at_payload(), key=ctx.k.t1)), 'duplicate-member')


@case('negative_tests#case-variant', expected='大文字小文字だけが違う値は別の値として扱い、照合に通らない', title='大文字小文字の違い')
def case_variant(ctx, r):
    api = ctx.api()
    r.reject('tenant_id="T1"（iss は t1）', _list(api, ctx.tok(changed(at_payload(), [NS, 'tenant_id'], 'T1'))), 'tenant-iss-mismatch')
    r.reject('パスのテナントが T1（トークンは t1）', _list(api, ctx.tok(), 'T1'), 'tenant-path-mismatch')
    r.reject('user_id が sub の大文字', _list(api, ctx.tok(changed(at_payload(), [NS, 'user_id'], 'ALICE-SUB'))), 'user-id-mismatch')
    c = api.authorize(ctx.tok(changed(at_payload(), [NS, 'roles'], ['Approver', 'TENANT-ADMIN'])), 't1', NOW)
    r.add('roles=["Approver","TENANT-ADMIN"]（語彙と大文字小文字が違う）', 'ロールとして数えない（[]）', c['roles'], c['roles'] == [])
    r.reject('aud="Saas-Api"', _list(api, ctx.tok(changed(at_payload(), ['aud'], 'Saas-Api'))), 'aud-mismatch')


# ================================================================ tenants and objects (scenario A)
@case('negative_tests#tenant-mismatch', expected='tenant-iss-mismatch・tenant-path-mismatch・claim-type で拒否', title='別テナント・テナントの食い違い')
def tenant_mismatch(ctx, r):
    api = ctx.api()
    bob = ctx.tok(at_payload('t2', 'bob-sub'), tenant='t2')
    r.reject('t2 のトークンでパス /t1 を一覧', _list(api, bob, 't1'), 'tenant-path-mismatch')
    r.reject('t2 のトークンでパス /t1、ヘッダー X-Tenant: t1（ケーススタディ A5）', _list(api, bob, 't1', headers={'X-Tenant': 't1'}), 'tenant-path-mismatch')
    rogue = ctx.tok(changed(at_payload('t2', 'bob-sub'), [NS, 'tenant_id'], 't1'), tenant='t2')
    r.reject('t2 の管理者が自分のレルムのマッパーで tenant_id=t1 を出させた（iss t2・t2 の鍵、ケーススタディ A8）', _list(api, rogue, 't1'), 'tenant-iss-mismatch')
    multi = ctx.tok(changed(at_payload(), [NS, 'tenant_id'], ['t1', 't2']))
    r.reject('tenant_id が配列 ["t1","t2"]（ケーススタディ A12）', _list(api, multi), 'claim-type')
    for v in ('', 'x' * 33):
        r.reject(f'tenant_id={v[:8]!r}…（{len(v)} バイト）', _list(api, ctx.tok(changed(at_payload(), [NS, 'tenant_id'], v))), 'claim-value')
    r.accept('t2 のトークンで /t2（正規）', _list(api, bob, 't2'))


@case('negative_tests#bola-other-owner', expected='他人の請求書は not-found（他テナントと同じ答え）', title='BOLA：他人のオブジェクト')
def bola(ctx, r):
    api = ctx.api()
    t = ctx.tok()
    r.accept('alice が自分の請求書 2 を読む', lambda: api.get_invoice(t, 't1', 2, NOW))
    r.reject('alice が同じテナントの carol の請求書 3 を読む', lambda: api.get_invoice(t, 't1', 3, NOW), 'not-found')
    r.reject('alice が t2 の請求書 1 を読む（ケーススタディ A6）', lambda: api.get_invoice(t, 't1', 1, NOW), 'not-found')
    p = changed(at_payload(), [NS, 'user_id'], 'carol-sub')
    r.reject('user_id だけを carol にしたトークン（sub は alice）', lambda: api.get_invoice(ctx.tok(p), 't1', 3, NOW), 'user-id-mismatch')


@case('negative_tests#revocation-latency', expected='テナントの停止は次の要求で拒否（0 秒）。ロールの剥奪は受け入れの上限（330 秒）の後に効く', title='剥奪の反映（オフライン）')
def revocation_offline(ctx, r):
    store = MemoryStore()
    api = ctx.api(store=store)
    t = ctx.tok()
    r.accept('停止前の要求', _list(api, t))
    store.tenants['t1'] = 'suspended'
    r.reject('テナントを停止した直後の要求（AT の exp を待たない、ケーススタディの volatility 0）', _list(api, t, now=NOW + 1), 'tenant-suspended')
    store.tenants['t1'] = 'active'
    ctx_ = api.authorize(t, 't1', NOW + 330)
    r.add('ロールを外した後も、手元の AT は発行から 330 秒まで approver のまま', 'approver が残る（上限 330 秒の内側）', ctx_['roles'], ctx_['roles'] == ['approver'])
    r.reject('発行から 331 秒で、その AT は使えない', _list(api, t, now=NOW + 331), 'expired')
    r.note('Keycloak を使う版（lifetime_revocation.md）で、剥奪からリフレッシュで新しい AT に替わるまでの時間を測る')


# ================================================================ scenario B: propagation and delegation
def _ledger(ctx):
    led = B.Ledger(ctx.k.jwks_b())
    led.record_start(txn_payload())
    return led


@case('negative_tests#txn-token-as-at', expected='Authorization ヘッダーの Txn-Token は txn-token-in-authorization、AT の受け手では typ-mismatch', title='Txn-Token を AT として送る')
def txn_as_at(ctx, r):
    led = _ledger(ctx)
    t = mint_txn(ctx.k)
    r.reject('ledger に Authorization: Bearer <Txn-Token>', lambda: led.accept({'Authorization': 'Bearer ' + t}, {'operation': 'ledger.read'}, B.ORDERS_ID, NOW), 'txn-token-in-authorization')
    tts, _ = B.load_design()
    from validator import JwksCache, TokenValidator
    orders = TokenValidator(tts['INT_AT'], 'orders', JwksCache({'https://sts.corp.example.com': {'keys': [ctx.k.sts.jwk()]},
                                                              'https://tts.corp.example.com': {'keys': [ctx.k.tts.jwk()]}}))
    r.reject('orders（INT_AT の受け手）に Txn-Token を AT として送る', lambda: orders.verify(t, NOW), 'typ-mismatch')


@case('negative_tests#txn-remint-immutable', expected='txn・sub・aud・req_wl を変えた、または scope を広げた Txn-Token は txn-changed で拒否', title='Txn-Token の作り直しで不変であるべきもの')
def txn_remint(ctx, r):
    led = _ledger(ctx)
    for name, path, val in (('txn を変えた', ['txn'], 'txn-0002'), ('sub を変えた', ['sub'], 'emp-0002'),
                            ('aud を変えた', ['aud'], 'https://partner.example.com'), ('scope を広げた（ledger.post）', ['scope'], 'orders.read ledger.read ledger.post')):
        p = changed(txn_payload(), path, val)
        if path == ['txn']:
            led.record_start(changed(txn_payload(), ['txn'], 'txn-0002-original'))
        r.reject(f'TTS が作り直して {name}（署名は正しい）', lambda p=p: led.accept({'Txn-Token': mint_txn(ctx.k, p)}, {'operation': 'ledger.read'}, B.ORDERS_ID, NOW),
                 ('txn-changed', 'unknown-txn', 'aud-mismatch'))
    found = B.remint_violations(txn_payload(), changed(txn_payload(), ['exp'], NOW + 900))
    r.add('作り直しで exp を延ばした（検査の関数）', '指摘あり', found, bool(found))
    r.add('改変せずに渡した（正規）', '指摘なし', B.remint_violations(txn_payload(), txn_payload()), not B.remint_violations(txn_payload(), txn_payload()))


@case('negative_tests#nested-act', expected='入れ子の act だけを変えたトークンを拒否。今の代理者は最も外側の act.sub だけ', lint=['L12'], title='入れ子の act')
def nested_act(ctx, r):
    inv = B.Invoices(ctx.k.jwks_b(), approvals={'appr-1': 'active'})
    body = {'invoice': 'inv-1', 'amount': 120000, 'creditor': 'JP00-1234-5678'}
    p = changed(task_payload(), ['act', 'act', 'sub'], 'admin-console')
    r.reject('入れ子の act.act.sub だけを admin-console に変えた（署名は正しい）', lambda: inv.pay(mint_sts(ctx.k, p), body, B.MCP_ID, NOW), 'delegation-chain-mismatch')
    p = changed(task_payload(), ['act'], {'sub': 'admin-console', 'act': {'sub': 'invoice-mcp', 'act': {'sub': 'agent:expense'}}})
    r.reject('最も外側を admin-console にし、invoice-mcp を内側に入れた（内側を読む受け手なら通る）', lambda: inv.pay(mint_sts(ctx.k, p), body, B.MCP_ID, NOW), 'actor-mismatch')
    p = changed(task_payload(), ['act', 'act', 'act'], {'sub': 'x', 'act': {'sub': 'y'}})
    r.reject('委任の連鎖の深さ 4（組織の規則は 3 まで）', lambda: inv.pay(mint_sts(ctx.k, p), body, B.MCP_ID, NOW), 'delegation-too-deep')
    r.reject('最も外側の act.sub と mTLS の相手が違う', lambda: inv.pay(mint_sts(ctx.k, task_payload()), body, 'other-tool', NOW), 'actor-mismatch')
    p = changed(task_payload(), ['act'], DELETE)
    r.reject('act が無い（利用者のトークンを借りた形、ケーススタディ C12）', lambda: inv.pay(mint_sts(ctx.k, p), body, B.MCP_ID, NOW), 'missing-claim')
    r.accept('正規の連鎖（invoice-mcp ← agent:expense）', lambda: inv.pay(mint_sts(ctx.k, task_payload()), body, B.MCP_ID, NOW))


@case('negative_tests#req-wl-changed', expected='req_wl だけを変えたトークンを拒否', title='req_wl だけを変えた')
def req_wl_changed(ctx, r):
    led = _ledger(ctx)
    good = mint_txn(ctx.k)
    h, _, s = good.split('.')
    tampered = h + '.' + b64e(json.dumps(changed(txn_payload(), ['req_wl'], 'spiffe://corp.example.com/orders'), separators=(',', ':')).encode()) + '.' + s
    r.reject('req_wl だけを書き換えた（署名はそのまま）', lambda: led.accept({'Txn-Token': tampered}, {'operation': 'ledger.read'}, B.ORDERS_ID, NOW), 'bad-signature')
    p = changed(txn_payload(), ['req_wl'], 'spiffe://corp.example.com/orders')
    r.reject('TTS が req_wl=orders で発行した（入口以外が Txn-Token を求めた）', lambda: led.accept({'Txn-Token': mint_txn(ctx.k, p)}, {'operation': 'ledger.read'}, B.ORDERS_ID, NOW), 'req-wl-not-allowed')
    r.reject('mTLS の相手が orders でない', lambda: led.accept({'Txn-Token': good}, {'operation': 'ledger.read'}, 'spiffe://corp.example.com/docs', NOW), 'peer-mismatch')


@case('negative_tests#tctx-mismatch', expected='本文の操作が tctx と食い違う要求を拒否', lint=['L11'], title='本文と tctx の食い違い')
def tctx_mismatch(ctx, r):
    led = _ledger(ctx)
    t = mint_txn(ctx.k)
    r.reject('本文の operation=ledger.post、tctx は ledger.read', lambda: led.accept({'Txn-Token': t}, {'operation': 'ledger.post'}, B.ORDERS_ID, NOW), 'tctx-body-mismatch')
    p = txn_payload(scope='orders.read ledger.read', operation='ledger.post')
    led.record_start(p)
    r.reject('tctx.operation=ledger.post（scope は ledger.read）', lambda: led.accept({'Txn-Token': mint_txn(ctx.k, p)}, {'operation': 'ledger.post'}, B.ORDERS_ID, NOW), 'tctx-scope-mismatch')
    p = changed(txn_payload(), ['tctx'], {'operation': 'ledger.read', 'amount': 1})
    led.record_start(p)
    r.reject('tctx に語彙に無い項目（amount）', lambda: led.accept({'Txn-Token': mint_txn(ctx.k, p)}, {'operation': 'ledger.read'}, B.ORDERS_ID, NOW), 'tctx-shape')
    r.note('シナリオ B の tctx の項目は operation だけ（claims.yaml C-tctx の value_vocabulary）。#8 の本文の「本文の数量」は、この記入例では承認の金額（approval-mismatch）で確かめる')


@case('negative_tests#approval-mismatch', expected='承認と食い違う金額・相手先・対象、取り消した承認を拒否', lint=['L11'], title='承認の内容と要求の食い違い')
def approval_mismatch(ctx, r):
    appr = {'appr-1': 'active'}
    inv = B.Invoices(ctx.k.jwks_b(), approvals=appr)
    t = mint_sts(ctx.k, task_payload())
    ok = {'invoice': 'inv-1', 'amount': 120000, 'creditor': 'JP00-1234-5678'}
    r.reject('金額を 1,200,000 に変えた（ケーススタディ C5）', lambda: inv.pay(t, dict(ok, amount=1200000), B.MCP_ID, NOW), 'approval-mismatch')
    r.reject('相手先の口座を変えた（C6）', lambda: inv.pay(t, dict(ok, creditor='JP99-0000-0000'), B.MCP_ID, NOW), 'approval-mismatch')
    p = changed(task_payload(), ['authorization_details'], [])
    r.reject('authorization_details が空', lambda: inv.pay(mint_sts(ctx.k, p), ok, B.MCP_ID, NOW), 'approval-missing')
    appr['appr-1'] = 'revoked'
    r.reject('承認を取り消した後（C7。トークンの exp を待たない）', lambda: inv.pay(t, ok, B.MCP_ID, NOW), 'approval-not-active')


@case('negative_tests#passthrough-rejected', expected='MCP サーバー宛ての AGENT_AT を上流の invoices に送ると aud-mismatch', title='トークンのパススルー')
def passthrough(ctx, r):
    inv = B.Invoices(ctx.k.jwks_b(), approvals={'appr-1': 'active'})
    t = mint_sts(ctx.k, agent_payload())
    ok = {'invoice': 'inv-1', 'amount': 120000, 'creditor': 'JP00-1234-5678'}
    r.reject('invoice-mcp が受けた AGENT_AT をそのまま invoices に送る（ケーススタディ C2）', lambda: inv.pay(t, ok, B.MCP_ID, NOW), 'aud-mismatch')
    p = changed(agent_payload(), ['aud'], ['invoice-mcp', 'invoices'])
    r.reject('宛先を複数にした広いトークン（C13。H14 は invoice-mcp だけ）', lambda: inv.pay(mint_sts(ctx.k, p), ok, B.MCP_ID, NOW), ('actor-mismatch', 'delegation-chain-mismatch'))
    r.note('2 つ目は aud には invoices を含むので aud の検査は通り、act（agent:expense が今の代理者）で落ちる。宛先を 1 つにする規則は発行者（sts）と L16 で守る')


@case('negative_tests#rar-unknown-type', expected='知らない type・フィールド・actions の authorization_details を sts が invalid_authorization_details で拒否', title='知らない authorization_details')
def rar_unknown(ctx, r):
    ok = task_payload()['authorization_details']
    r.accept('承認の形どおり', lambda: B.sts_check_authorization_details(ok))
    r.reject('type が https://claims.example.com/rar/refund', lambda: B.sts_check_authorization_details([dict(ok[0], type='https://claims.example.com/rar/refund')]), 'invalid_authorization_details')
    r.reject('知らないフィールド maxAmount', lambda: B.sts_check_authorization_details([dict(ok[0], maxAmount=10**9)]), 'invalid_authorization_details')
    r.reject('actions に refund', lambda: B.sts_check_authorization_details([dict(ok[0], actions=['pay', 'refund'])]), 'invalid_authorization_details')


@case('negative_tests#spoofed-identity-header', expected='x-user-* はどの綴りでも除去、重複は duplicate-header で拒否。素朴な除去は変種を通す', title='ID 系ヘッダーの偽装')
def spoofed_headers(ctx, r):
    variants = [('X-User-Id', 'emp-9999'), ('x-user-id', 'emp-9999'), ('X_USER_ID', 'emp-9999'), ('x-User_Roles', 'admin'), (' X-User-Department', 'finance')]
    for h in variants:
        out = B.edge_filter([('Authorization', 'Bearer t'), h])
        r.add(f'{h[0]!r} を入口で除去', '除去される', [n for n, _ in out], all(not B.norm_header(n).startswith('x-user-') for n, _ in out))
    r.reject('x-user-id が 2 回（大文字小文字違い）', lambda: B.edge_filter([('X-User-Id', 'a'), ('x-user-id', 'b')]), 'duplicate-header')
    r.reject('Authorization が 2 回', lambda: B.edge_filter([('Authorization', 'Bearer a'), ('authorization', 'Bearer b')]), 'duplicate-header')
    r.reject('X_User_Id と X-User-Id（_ と - の変種の重複）', lambda: B.edge_filter([('X_User_Id', 'a'), ('X-User-Id', 'b')]), 'duplicate-header')
    leaked = [n for n, _ in naive_out(variants)]
    r.add('素朴な除去（X-User-Id の完全一致だけ）は変種を通す＝このテストが見つける誤り', '4 件以上が残る', leaked, len(leaked) >= 4)
    api = ctx.api()
    bob = ctx.tok(at_payload('t2', 'bob-sub'), tenant='t2')
    rows = api.list_invoices(bob, 't2', NOW, headers={'X-Tenant': 't1', 'x_tenant': 't1'})
    r.add('シナリオ A の API は X-Tenant を読まない', 't2 の行だけ', [x['tenant_id'] for x in rows], all(x['tenant_id'] == 't2' for x in rows))


def naive_out(variants):
    return B.naive_edge_filter(list(variants))


# ================================================================ exchange narrowing (runtime L16)
H15 = {'aud_replacement': True, 'aud': ['invoices']}


@case('negative_tests#exchange-narrowing', expected='交換で出たトークンが上流を超えたら指摘する。正規の交換は指摘 0', lint=['L16'], title='交換で絞られているか（オフライン）')
def exchange_offline(ctx, r):
    up = agent_payload()
    down = task_payload()
    r.add('H14→H15 の正規の交換', '指摘 0', narrowing.check(up, down, H15), not narrowing.check(up, down, H15))
    for name, path, val in (('scope に invoices.refund を足した', ['scope'], 'invoices.pay invoices.refund'),
                            ('aud に orders を足した', ['aud'], ['invoices', 'orders']),
                            ('exp を上流より 600 秒延ばした', ['exp'], up['exp'] + 600),
                            ('承認の金額を変えた', ['authorization_details', 0, 'instructedAmount'], 999999),
                            ('独自クレーム department を足した', [NS, 'department'], 'finance'),
                            ('tenant_id を変えた', [NS, 'tenant_id'], 'other')):
        d = changed(down, path, val)
        f = narrowing.check(up, d, H15)
        r.add(f'作った TASK_AT で {name}', '指摘あり', f, bool(f))
    fx = json.load(open(os.path.join(HERE, 'fixtures', 'kc_exchange_casestudy.json'), encoding='utf-8'))
    kc_hop = {'aud_replacement': True, 'aud': ['invoices']}
    for probe in ('narrow_to_invoices', 'scope_not_granted'):
        d = fx['probes'][probe]
        f = narrowing.check(fx['subject'], d, kc_hop, audience_scopes=fx['audience_scopes'])
        want = probe == 'scope_not_granted'
        r.add(f'ケーススタディの実測 {probe}（aud={d["aud"]}）', '指摘あり（orders が出た）' if want else '指摘 0', f, bool(f) == want)


# ================================================================ consumer contract
def _golden_kc():
    d = json.load(open(os.path.join(ROOT, 'tools', 'tests', 'fixtures', 'claim_lint', 'golden', 'token.json'), encoding='utf-8'))
    return json.loads(d['payload_json'])


def _reads(api, token, tenant='t1', now=NOW):
    log = set()
    api.validator.wrap = lambda p: contract.Recording(p, log)
    try:
        api.list_invoices(token, tenant, now)
    finally:
        api.validator.wrap = None
    return log


@case('consumer_contract#declared-reads', expected='受け手が読むクレームはすべて台帳の consumers に受け手がある。consumers から外すと失敗する', title='読むクレームの宣言')
def declared_reads(ctx, r):
    api = ctx.api()
    _, claims = load_design(DESIGN)
    rows = list(claims.values())
    log = _reads(api, ctx.tok())
    r.add('参照の saas-api が読んだメンバー', '台帳のどれかの行', sorted(f'{a}{b}' for a, b in log), True)
    v = contract.violations(log, rows, 'saas-api')
    r.add('台帳のとおり（consumers に saas-api）', '違反 0', v, not v)
    e = contract.schema_errors(at_payload(), os.path.join(DESIGN, 'schemas', 'AT.consumer.schema.json'))
    r.add('読むクレームの型：台帳から生成した今の版の consumer のスキーマ（AT.consumer.schema.json）', 'スキーマの誤り 0', e, not e)
    for cid in ('C-roles', 'C-tenant-id', 'C-azp'):
        rows2 = copy.deepcopy(rows)
        for row in rows2:
            if row['id'] == cid:
                row['consumers'] = [c for c in row['consumers'] if c != 'saas-api']
        v2 = contract.violations(log, rows2, 'saas-api')
        r.add(f'{cid} の consumers から saas-api を外す', '契約テストが失敗する（違反 1 件以上）', v2, any(cid in x for x in v2))
    p = dict(at_payload(), email='alice@example.com')
    log3 = set()
    api.validator.wrap = lambda q: contract.Recording(q, log3)
    api.list_invoices(ctx.tok(p), 't1', NOW)
    api.validator.wrap = None
    r.add('受け手が email を読まないこと（AT に載せない宣言と一致）', 'email を読まない', ('', 'email') in log3, ('', 'email') not in log3)


@case('consumer_contract#unknown-claim-ignored', expected='未知のクレームを足しても受理する', title='未知のクレームを無視する')
def unknown_ignored(ctx, r):
    api = ctx.api()
    p = dict(at_payload(), x_feature_flag=True, new_top_level={'a': 1})
    r.accept('最上位に未知のクレーム 2 つ', _list(api, ctx.tok(p)))
    p = changed(at_payload(), [NS, 'department'], 'sales')
    r.accept('名前空間に未知の department', _list(api, ctx.tok(p)))


@case('consumer_contract#issued-claims-present', expected='発行されたトークンに、台帳で AT に載ると宣言した採用の独自クレームが全部ある', title='発行されたトークンの黙った欠落')
def issued_present(ctx, r):
    _, claims = load_design(DESIGN)
    rows = list(claims.values())
    g = _golden_kc()
    m = contract.issued_claims_missing(g, rows, 'AT')
    r.add('Keycloak 26.8 が発行した見本（tools/tests/fixtures/claim_lint/golden/token.json）', '欠落 0', m, not m)
    light = {k: v for k, v in g.items() if k in ('azp', 'exp', 'iat', 'iss', 'jti', 'scope', 'sid', 'typ')}
    m = contract.issued_claims_missing(light, rows, 'AT')
    r.add('軽量アクセストークンの形（ケーススタディ keycloak.lightweight の light_claims）', '欠落を検出', m, bool(m))


@case('consumer_contract#type-shape-match', expected='発行されたトークンが台帳から生成した issuer 適合のスキーマ（型・形）に合う', title='型と形の一致')
def type_shape(ctx, r):
    sch = os.path.join(DESIGN, 'schemas', 'AT.issuer.schema.json')
    g = _golden_kc()
    e = contract.schema_errors(g, sch)
    r.add('Keycloak 26.8 の見本', 'スキーマの誤り 0', e, not e)
    for name, path, val in (('roles が文字列', [NS, 'roles'], 'approver'), ('tenant_id が配列', [NS, 'tenant_id'], ['t1']),
                            ('v が数値', [NS, 'v'], 1), ('知らないクレームを足した', ['x_new'], 1)):
        e = contract.schema_errors(changed(g, path, val), sch)
        r.add(f'見本を変えて {name}', 'スキーマの誤りあり', e[:2], bool(e))


@case('consumer_contract#format-change-cases', expected='形式の変化ごとに、どの検査が見つけるかを示す（型だけの契約の死角を含む）', title='契約テストが見逃しやすい変更')
def format_changes(ctx, r):
    api = ctx.api()
    cons = os.path.join(DESIGN, 'schemas', 'AT.consumer.schema.json')
    iss_s = os.path.join(DESIGN, 'schemas', 'AT.issuer.schema.json')
    cases = [
        ('区切り文字：roles を配列から空白区切りの文字列に', [NS, 'roles'], 'approver tenant-admin', True),
        ('区切り文字：roles の要素をカンマで連結した 1 要素に', [NS, 'roles'], ['approver,tenant-admin'], False),
        ('大文字化：tenant_id を T1 に', [NS, 'tenant_id'], 'T1', False),
        ('2^53 を超える数値：user_id を数値 9007199254740993 に', [NS, 'user_id'], 9007199254740993, True),
        ('null：roles を null に', [NS, 'roles'], None, True),
        ('false：tenant_id を false に', [NS, 'tenant_id'], False, True),
        ('真偽値の文字列化：v を "true" に（版の値の取り違え）', [NS, 'v'], 'true', False),
        ('制限のクレームの追加：名前空間に read_only: true', [NS, 'read_only'], True, False),
    ]
    for name, path, val, type_catches in cases:
        p = changed(at_payload(), path, val)
        ce = contract.schema_errors(p, cons)
        ie = contract.schema_errors(p, iss_s)
        try:
            api.list_invoices(ctx.tok(p), 't1', NOW)
            api_res = 'accepted'
        except Reject as e:
            api_res = e.code
        obs = {'consumer_schema': 'detect' if ce else 'miss', 'issuer_schema': 'detect' if ie else 'miss', 'reference_api': api_res}
        caught = bool(ie) or api_res != 'accepted'
        r.add(name, f'型だけの契約は{"見つける" if type_catches else "見逃す"}。issuer 適合のスキーマか参照の受け手のどちらかが見つける',
              obs, (bool(ce) == type_catches) and caught)
    big = '{"n":9007199254740993}'
    as_float = json.loads(big, parse_float=float, parse_int=float)['n']
    r.add('2^53 を超える整数を倍精度で読む受け手（JavaScript の Number と同じ）', '値が変わる', int(as_float), int(as_float) != 9007199254740993)
    r.note('シナリオ A の AT に真偽値のクレームはない。真偽値の文字列化は、版の値 v（文字列の語彙）で代えた')
