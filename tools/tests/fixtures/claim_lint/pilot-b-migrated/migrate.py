# -*- coding: utf-8 -*-
"""Make this fixture from the pilot design of scenario B (research/pilot/scenario-b, #9), which is evidence and is not
edited: the same design, with the workarounds of its author replaced by the columns of #58 (registry 0.3.0).

  python tools/tests/fixtures/claim_lint/pilot-b-migrated/migrate.py           # rewrite the fixture
  python tools/tests/fixtures/claim_lint/pilot-b-migrated/migrate.py --check   # the committed fixture is what this makes

What changes (README.md of this directory has the before / after table):
  1  catalog_answers.yaml  idp: one IdP -> the five IdPs, each with the token types it issues
  2  claims.yaml           rows for the IdP-defined claims the entry reads (idp_defined), with on_missing and
                           identifier_properties; token_types.yaml required_claims name them
  3  hops.yaml             H7 / H8: upstream (the five entry hops), added_claims, aud_mapping
  4  token_types.yaml      COGNITO_AT: required_claims without aud, audience_claim: client_id
  5  token_types.yaml      typ is the header value only; kind_discriminator says which payload value tells the kinds apart
  6  token_types.yaml      issuance_profile.client_auth: exceptions for Cognito
Everything else is copied. The values are those of the pilot (written by an LLM, not verified by a person); facts added
here are the ones tools/claim_lint/idp_claims.yaml cites, and the client authentication methods of Cognito's token endpoint.
"""
import copy
import os
import shutil
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
SRC = os.path.join(ROOT, 'research', 'pilot', 'scenario-b')
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from claim_lint import core  # noqa: E402

VERSION = '0.3.0'
KC, ENTRA, OKTA, COGNITO, AUTH0 = 'keycloak', 'entra', 'okta', 'cognito', 'auth0'
ISS = {KC: 'https://kc.corp.example.com/realms/corp',
       ENTRA: 'https://login.microsoftonline.com/11111111-2222-3333-4444-555555555555/v2.0',
       OKTA: 'https://corp.okta.example.com/oauth2/default',
       COGNITO: 'https://cognito-idp.ap-northeast-1.amazonaws.com/ap-northeast-1_EXAMPLE'}
ENTRA_DOC = {'kind': 'spec', 'id': 'Microsoft identity platform「Access token claims reference」',
             'url': 'https://learn.microsoft.com/en-us/entra/identity-platform/access-token-claims-reference', 'verified_on': '2026-11-25'}
OKTA_DOC = {'kind': 'spec', 'id': 'Okta Developer「OpenID Connect & OAuth 2.0 API」Access token',
            'url': 'https://developer.okta.com/docs/api/openapi/okta-oauth/guides/overview/', 'verified_on': '2026-11-25'}
COGNITO_DOC = {'kind': 'spec', 'id': 'Amazon Cognito Developer Guide「Understanding the access token」',
               'url': 'https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-using-the-access-token.html',
               'verified_on': '2026-11-25'}
COGNITO_VERIFY = {'kind': 'spec', 'id': 'Amazon Cognito Developer Guide「Verifying JSON web tokens」',
                  'url': 'https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-using-tokens-verifying-a-jwt.html',
                  'verified_on': '2026-11-25'}
RFC8725 = {'kind': 'spec', 'id': 'RFC 8725 §3.12'}


def by_id(rows):
    return {r['id']: r for r in rows}


def idp_row(base, cid, name, idp, tt, **over):
    """A row for a claim that the IdP defines and the entry reads: the columns of a pilot row that the entry reads from an
    IdP token (base), with the name, the IdP and the token type replaced."""
    r = copy.deepcopy(base)
    for k in ('registered_ref', 'upstream_issuer', 'answers', 'does_not_answer', 'assumption', 'revisit_trigger', 'max_items',
              'typical_items', 'absent_semantics', 'identifier_properties', 'value_normalization', 'verification_method',
              'consumer_access_path', 'change_controller'):
        r.pop(k, None)
    r.update({'id': cid, 'name': name, 'namespace': None, 'idp_defined': {'idp': idp}, 'decision': '既定どおり',
              'issuers': [ISS[idp]], 'carried_in': [tt], 'consumers': ['gateway'],
              'authoritative_writer': [{'stage': '②', 'writer': f'{idp}（AT の発行時）', 'configurable_by': ['platform']}],
              'issue_events': ['I01', 'I02'], 'owner': '情報システム部 ID 基盤チーム', 'change_controller': f'{idp}（製品が決めた名前）'})
    r.update(over)
    order = ['id', 'name', 'namespace', 'idp_defined']
    return {**{k: r[k] for k in order}, **{k: v for k, v in r.items() if k not in order}}


def migrate_claims(doc):
    rows = by_id(doc['claims'])
    sub, client_id, groups, scope = rows['C-sub'], rows['C-client-id'], rows['C-groups'], rows['C-scope']
    ident = {'usage': 'identifier', 'identifier_properties': {'stable': True, 'reassignable': False, 'pairwise': False, 'id_scheme': 'opaque'},
             'value_normalization': {'case': 'as_is', 'unicode': 'none', 'trim': False, 'compare': 'exact', 'normalized_by': '入口'},
             'on_missing': '拒否', 'absent_semantics': {'absent': '利用者を決められないので拒む'}}
    new = [
        idp_row(sub, 'C-entra-oid', 'oid', ENTRA, 'ENTRA_AT', **ident, type='string', shape='single', refs=[ENTRA_DOC],
                description='Entra ID のテナントの中で、利用者（かサービスプリンシパル）を表す不変の ID（GUID）',
                not_meaning='sub ではない（Entra の sub はアプリごとに違う）。テナントが違えば同じ人でも別の値になるので、tid と組で使う',
                rationale='入口は Entra の AT では（tid, oid）で社員台帳の名寄せの表を引く（P5 の 1.）。無ければ利用者を決められないので拒む（パイロットの指摘 B-R1 F01・B-R2 R2-03）',
                source_system='Entra ID の利用者のオブジェクト',
                enforced_at=[{'service': 'gateway', 'check': '（tid, oid）が社員台帳の名寄せの表にあり、在籍していること', 'against': ['iss', 'data_layer']}]),
        idp_row(client_id, 'C-entra-tid', 'tid', ENTRA, 'ENTRA_AT', usage='authz', type='string', shape='single', refs=[ENTRA_DOC],
                description='利用者がサインインした Entra ID のテナントの ID（GUID）',
                not_meaning='組織の顧客のテナントではない（この設計はマルチテナントでない）。iss の中のテナントの ID と同じ値',
                rationale='入口は tid が自社のテナントの ID と一致することを確かめ、oid と組で名寄せに使う。別のテナントの AT を拒む',
                source_system='Entra ID のテナント', on_missing='拒否',
                enforced_at=[{'service': 'gateway', 'check': '自社のテナントの ID と完全一致し、iss の中のテナントの ID とも一致する', 'against': ['api_config', 'iss']}],
                pii_category='該当なし', data_category=['system.operations'], log_policy='記録する'),
        idp_row(scope, 'C-entra-scp', 'scp', ENTRA, 'ENTRA_AT', usage='authz', type='string', shape='space_delimited', max_items=10, max_bytes=32, refs=[ENTRA_DOC],
                description='クライアントが同意を得た、API のスコープ（空白区切りの 1 つの文字列）',
                not_meaning='利用者のロールではない。Okta の scp（配列）とは形が違う',
                rationale='入口は scp が経路のサービスのスコープを含むことを確かめる', source_system='Entra ID のアプリ登録（公開するスコープ）',
                on_missing='拒否', enforced_at=[{'service': 'gateway', 'check': '経路のサービス（orders・invoices）のスコープを含む', 'against': ['api_config']}]),
        idp_row(sub, 'C-okta-uid', 'uid', OKTA, 'OKTA_AT', **ident, type='string', shape='single', refs=[OKTA_DOC],
                description='Okta の利用者を一意に表す ID',
                not_meaning='sub ではない（Okta の AT の sub は再利用されうるログイン名で、この設計は読まない）。利用者に結びつかない AT には載らない',
                rationale='入口は Okta の AT では uid で社員台帳の名寄せの表を引く（P5 の 1.）。無ければ拒む（client credentials の AT を利用者の要求として受けない）',
                source_system='Okta の利用者のプロファイル',
                enforced_at=[{'service': 'gateway', 'check': '（iss, uid）が社員台帳の名寄せの表にあり、在籍していること', 'against': ['iss', 'data_layer']}]),
        idp_row(client_id, 'C-okta-cid', 'cid', OKTA, 'OKTA_AT', usage='authz', type='string', shape='single', refs=[OKTA_DOC],
                description='AT を求めたクライアントの ID', not_meaning='利用者ではない。宛先（aud）でもない',
                rationale='Okta の aud は api://default で注文と請求書に共通なので、入口は cid がポータルのクライアントであることを確かめる',
                source_system='Okta のアプリの登録', on_missing='拒否',
                enforced_at=[{'service': 'gateway', 'check': 'ポータルのクライアント ID と完全一致', 'against': ['api_config']}]),
        idp_row(scope, 'C-okta-scp', 'scp', OKTA, 'OKTA_AT', usage='authz', type='string', shape='array', max_items=10, max_bytes=32, refs=[OKTA_DOC],
                description='AT に認められたスコープの配列', not_meaning='利用者のロールではない。Entra の scp（空白区切りの文字列）とは形が違う',
                rationale='Okta の aud は共通なので、入口は scp で経路のサービスを確かめる', source_system='Okta の認可サーバーのスコープ',
                on_missing='拒否', overflow_strategy='発行を失敗させる',
                enforced_at=[{'service': 'gateway', 'check': '経路のサービス（orders・invoices）のスコープを含む', 'against': ['api_config']}]),
        idp_row(client_id, 'C-cognito-token-use', 'token_use', COGNITO, 'COGNITO_AT', usage='protocol', type='string', shape='single',
                allowed_values={'enum': ['access']},
                refs=[COGNITO_DOC, COGNITO_VERIFY],
                description='トークンの用途。AT では access', not_meaning='権限ではない。ID トークンでは id になる',
                rationale='Cognito の AT と ID トークンはヘッダーで区別できないので、入口は token_use が access のものだけを AT として受ける（ID トークンを API に出す取り違えを拒む）',
                source_system='Cognito（発行時に付ける）', on_missing='拒否',
                enforced_at=[{'service': 'gateway', 'check': 'access と完全一致', 'against': ['api_config']}]),
        idp_row(groups, 'C-cognito-groups', 'cognito:groups', COGNITO, 'COGNITO_AT', usage='authz', type='string', shape='array', refs=[COGNITO_DOC],
                description='利用者が属するユーザープールのグループの名前', not_meaning='組織のロールそのものではない。入口が写しの表でロールに替える',
                rationale='入口は Cognito のグループを組織のロール（C-roles）に替える。グループの無い利用者（B16）はロールなしで通す',
                source_system='Cognito のユーザープールのグループ', max_items=50, typical_items=3, on_missing='無視',
                absent_semantics={'absent': 'グループに属さない利用者。ロールを空にする（既定のロールを使わない）'},
                enforced_at=[{'service': 'gateway', 'check': '写しの表にあるグループだけを組織のロールに替える', 'against': ['api_config']}]),
        idp_row(groups, 'C-kc-realm-access', 'realm_access', KC, 'KC_AT', usage='authz', type='object', shape='single',
                refs=[{'kind': 'guide-slide', 'id': 'p03-keycloak-mappers'}],
                description='Keycloak のレルムのロール（realm_access.roles の配列）を入れるオブジェクト',
                not_meaning='組織のロールそのものではない。入口が写しの表でロールに替える',
                rationale='入口は realm_access.roles を組織のロール（C-roles）に替える。サービスには Keycloak の形のまま渡さない',
                source_system='Keycloak のレルムのロールの割り当て', max_bytes=1024, on_missing='無視',
                overflow_strategy='上限で固定（超えない値域）',
                absent_semantics={'absent': 'レルムのロールの無い利用者。ロールを空にする（既定のロールを使わない）'},
                enforced_at=[{'service': 'gateway', 'check': '写しの表にあるロールだけを組織のロールに替える', 'against': ['api_config']}]),
        idp_row(client_id, 'C-kc-typ', 'typ', KC, 'KC_AT', usage='protocol', type='string', shape='single', refs=[RFC8725],
                allowed_values={'enum': ['Bearer']},
                description='Keycloak がペイロードに書くトークンの種類。AT では Bearer', not_meaning='ヘッダーの typ（JWT）ではない。ID トークンでは ID になる',
                rationale='Keycloak の AT と ID トークンはヘッダーの typ が同じ JWT なので、入口はペイロードの typ が Bearer のものだけを AT として受ける',
                source_system='Keycloak（発行時に付ける）', on_missing='拒否',
                enforced_at=[{'service': 'gateway', 'check': 'Bearer と完全一致', 'against': ['api_config']}]),
    ]
    # the new rows go after the last adopted row (before the rejected rows)
    last = max(i for i, r in enumerate(doc['claims']) if r.get('decision') != '却下')
    doc['claims'][last + 1:last + 1] = new
    return doc


def migrate_token_types(doc):
    tt = by_id(doc['token_types'])
    # 6: per-IdP exception of the issuance profile (was: only in the rationale text)
    doc['issuance_profile']['client_auth']['exceptions'] = [
        {'idp': COGNITO, 'value': 'client_secret_basic',
         'rationale': 'Cognito のトークンエンドポイントが対応するクライアント認証は client_secret_basic と client_secret_post（private_key_jwt は挙がっていない）ので、クライアントの秘密で認証する',
         'refs': [{'kind': 'spec', 'id': 'Amazon Cognito Developer Guide「The token endpoint」',
                   'url': 'https://docs.aws.amazon.com/cognito/latest/developerguide/token-endpoint.html', 'verified_on': '2026-11-25'}]}]
    # 5: typ is the header value; the payload value that tells the kinds apart goes to kind_discriminator
    tt['KC_AT'].update({'typ': 'JWT', 'kind_discriminator': [{'claim': 'typ', 'value': 'Bearer', 'note': 'ペイロードの typ。ID トークンは ID'},
                                                             {'claim': 'aud'}]})
    tt['ENTRA_AT'].update({'typ': 'JWT', 'kind_discriminator': [{'claim': 'aud', 'note': 'API の Application ID URI。ID トークンの aud はクライアントの ID'}]})
    tt['GRAPH_AT'].update({'typ': 'JWT', 'kind_discriminator': [{'claim': 'aud'}]})
    tt['ID_TOKEN'].update({'typ': 'JWT', 'kind_discriminator': [{'claim': 'aud', 'note': 'ポータルのクライアントの ID。API の宛先ではない'}]})
    tt['CLIENT_ASSERTION'].update({'typ': 'JWT', 'kind_discriminator': [{'claim': 'aud', 'note': 'IdP のトークンエンドポイント'}]})
    tt['OKTA_AT'].update({'typ': '(absent)', 'kind_discriminator': [{'claim': 'aud'}, {'claim': 'cid', 'value': 'portal'}]})
    tt['COGNITO_AT'].update({'typ': '(absent)', 'kind_discriminator': [{'claim': 'token_use', 'value': 'access'}, {'claim': 'aud', 'absent': True}]})
    # 4: Cognito's access token has no aud; the entry checks client_id
    tt['COGNITO_AT'].update({'audience_claim': 'client_id',
                             'required_claims': ['iss', 'sub', 'exp', 'iat', 'jti', 'client_id', 'scope', 'token_use']})
    # 2: the IdP-defined claims the entry cannot do without
    tt['KC_AT']['required_claims'] += ['typ']
    tt['ENTRA_AT']['required_claims'] += ['tid', 'oid', 'scp']
    tt['OKTA_AT']['required_claims'] += ['uid', 'cid', 'scp']
    for t in doc['token_types']:  # keep the columns in the order of the schema where the migration added one
        for key, after in (('kind_discriminator', 'typ'), ('audience_claim', 'aud'), ('required_claims', 'issuers')):
            if key in t and after in t:
                items = [(k, v) for k, v in t.items() if k != key]
                i = [k for k, _ in items].index(after) + 1
                items[i:i] = [(key, t[key])]
                t.clear()
                t.update(items)
    return doc


def migrate_hops(doc):
    hops = by_id(doc['hops'])
    hops['H2']['custom_claims'] += ['C-kc-realm-access', 'C-kc-typ']
    hops['H3']['custom_claims'] += ['C-entra-tid', 'C-entra-oid', 'C-entra-scp']
    hops['H4']['custom_claims'] += ['C-okta-uid', 'C-okta-cid', 'C-okta-scp']
    hops['H5']['custom_claims'] += ['C-cognito-token-use', 'C-cognito-groups']
    roles = {'claim': 'C-roles', 'source': 'upstream_claims',
             'from': ['C-kc-realm-access', 'C-groups', 'C-cognito-groups', 'C-auth0-roles'],
             'reason': 'IdP ごとのロール・グループのクレームを、入口が写しの表で組織のロールの語彙に替える（P5 の 1.）'}
    for hid, extra, svc in (('H7', {'claim': 'C-department', 'source': 'external_source', 'system': '社員台帳（人事システム）',
                                    'reason': '部署は IdP の AT に無く、入口が sub で社員台帳から引く（IdP の部署の属性は却下した）'}, 'orders'),
                            ('H8', {'claim': 'C-employee-id', 'source': 'external_source', 'system': '社員台帳（人事システム）',
                                    'reason': '社員番号は IdP の AT に無く、入口が sub で社員台帳から引く'}, 'invoices')):
        h = hops[hid]
        h.pop('note', None)  # the note said why upstream could not be written
        new = {}
        for k, v in h.items():
            new[k] = v
            if k == 'kind':
                new['upstream'] = ['H2', 'H3', 'H4', 'H5', 'H6']  # 3: the five entry hops (was: no upstream)
            if k == 'custom_claims':
                new['added_claims'] = [copy.deepcopy(roles), extra]
        new['aud_mapping'] = [{'upstream': 'H3', 'aud': svc, 'via': 'aud', 'value': f'api://{svc}'},
                              {'upstream': 'H4', 'aud': svc, 'via': 'scope', 'value': svc},
                              {'upstream': 'H5', 'aud': svc, 'via': 'scope', 'value': svc},
                              {'upstream': 'H6', 'aud': svc, 'via': 'scope', 'value': svc}]
        h.clear()
        h.update(new)
    return doc


def migrate_answers(doc):
    # 1: every IdP, with the token types it issues (was: keycloak only; the others only as URLs in searched)
    doc['idp'] = [
        {'name': KC, 'version': '26.8', 'token_types': ['KC_AT', 'ID_TOKEN', 'REFRESH_TOKEN', 'LOGOUT_TOKEN']},
        {'name': ENTRA, 'version': 'v2.0 エンドポイント', 'token_types': ['ENTRA_AT', 'GRAPH_AT', 'ID_TOKEN', 'REFRESH_TOKEN']},
        {'name': OKTA, 'version': 'カスタム認可サーバー（default）', 'token_types': ['OKTA_AT', 'ID_TOKEN', 'REFRESH_TOKEN']},
        {'name': COGNITO, 'version': 'ユーザープール', 'token_types': ['COGNITO_AT', 'ID_TOKEN', 'REFRESH_TOKEN'],
         'trigger_list_source': {'url': 'https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-lambda-pre-token-generation.html',
                                 'verified_on': '2026-11-25'},
         'trigger_list': [
             {'trigger': 'TokenGeneration_HostedAuth', 'events': ['I01']},
             {'trigger': 'TokenGeneration_RefreshTokens', 'events': ['I02']},
             {'trigger': 'TokenGeneration_Authentication',
              'out_of_scope': {'assumption': 'ポータルはマネージドログイン（認可コード＋PKCE）だけを使い、SDK の直接のサインイン（InitiateAuth）を使わない',
                               'breaks_when': 'ネイティブのアプリなど、ユーザープールの API で直接サインインするクライアントを足したとき'}},
             {'trigger': 'TokenGeneration_NewPasswordChallenge',
              'out_of_scope': {'assumption': '管理者が作った利用者の初回のパスワード変更は、マネージドログインの画面で行い、API のチャレンジを使わない',
                               'breaks_when': 'AdminCreateUser と API のチャレンジで初回のサインインを行うクライアントを足したとき'}},
             {'trigger': 'TokenGeneration_AuthenticateDevice',
              'out_of_scope': {'assumption': 'デバイスの記憶（device tracking）をユーザープールで有効にしない',
                               'breaks_when': 'デバイスの記憶を有効にしたとき'}},
             {'trigger': 'TokenGeneration_ClientCredentials',
              'out_of_scope': {'assumption': 'Cognito のアプリクライアントに client credentials を許さない（入口の client credentials は Keycloak と Entra だけ）',
                               'breaks_when': 'Cognito でマシン間の AT を出すアプリクライアントを足したとき'}},
         ]},
        {'name': AUTH0, 'version': 'テナント（模擬）', 'token_types': ['AUTH0_AT', 'ID_TOKEN', 'REFRESH_TOKEN']},
    ]
    return doc


HEAD = {
    'claims': '台帳。パイロット #9 のシナリオ B（research/pilot/scenario-b）を、#58 の列で書き直した fixture。migrate.py が作る（手で直さない）',
    'token_types': 'トークン目録と発行方式。パイロット #9 のシナリオ B を #58 の列で書き直した fixture。migrate.py が作る（手で直さない）',
    'hops': 'ホップ。パイロット #9 のシナリオ B を #58 の列で書き直した fixture。migrate.py が作る（手で直さない）',
    'catalog_answers': 'カタログへの回答。パイロット #9 のシナリオ B を #58 の列で書き直した fixture。migrate.py が作る（手で直さない）',
}
MIGRATIONS = {'claims': migrate_claims, 'token_types': migrate_token_types, 'hops': migrate_hops, 'catalog_answers': migrate_answers}


def build():
    out = {}
    for name, fn in MIGRATIONS.items():
        doc = fn(core.load_yaml(os.path.join(SRC, name + '.yaml')))
        lines = [f'# template_version: {VERSION}']
        if name != 'catalog_answers':
            lines.append(f'# yaml-language-server: $schema=../../../../../templates/registry/{name}.schema.json')
        lines.append(f'# {HEAD[name]}')
        body = yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=10000, default_flow_style=False)
        out[name + '.yaml'] = '\n'.join(lines) + '\n' + body
    for n in sorted(os.listdir(SRC)):
        if n.startswith('claim_request_') and n.endswith('.md'):  # the 25 questions (L72), copied as they are
            with open(os.path.join(SRC, n), encoding='utf-8') as f:
                out[n] = f.read()
    return out


def main(argv):
    want = build()
    if '--check' in argv:
        bad = []
        for n, text in want.items():
            p = os.path.join(HERE, n)
            if not os.path.isfile(p) or open(p, encoding='utf-8').read() != text:
                bad.append(n)
        print('migrate --check: ' + ('OK' if not bad else 'differs: ' + ', '.join(bad)))
        return 1 if bad else 0
    for n, text in want.items():
        with open(os.path.join(HERE, n), 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
    print(f'wrote {len(want)} files')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
